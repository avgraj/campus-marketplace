"""Server-side image pipeline (plan §7) — never trust the client.

- Confirms the bytes are really an image (Pillow), not just a .jpg filename.
- Strips EXIF metadata (phone GPS coordinates would leak seller location).
- Re-encodes to WebP at <=1600px, targeting ~300KB regardless of input.
- Enforces the 5MB raw upload cap.
"""

import io
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from ..config import settings


def _save_under_budget(img: Image.Image, dest: Path) -> None:
    """Re-encode at decreasing quality until under the target size."""
    for quality in (80, 70, 60, 50, 40):
        buf = io.BytesIO()
        try:
            img.save(buf, format="WEBP", quality=quality, method=4)
        except OSError:  # very old Pillow builds without WebP — fall back to JPEG
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= settings.target_image_bytes or quality == 40:
            dest.write_bytes(buf.getvalue())
            return


def process_image_upload(file: UploadFile) -> str:
    """Validate + process an uploaded image; returns the public URL path."""
    raw = file.file.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds the 5MB limit")
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # raises if the bytes aren't really an image
        img = Image.open(io.BytesIO(raw))  # verify() leaves the file unusable — reopen
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File is not a valid image") from None

    # Re-encoding from decoded pixels strips EXIF (incl. GPS) by construction.
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((settings.max_image_dimension, settings.max_image_dimension))

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(16)}.webp"
    _save_under_budget(img, upload_dir / filename)
    return f"/uploads/{filename}"
