"""Server-side image pipeline (plan §7) — never trust the client.

- Confirms the bytes are really an image (Pillow), not just a .jpg filename.
- Strips EXIF metadata (phone GPS coordinates would leak seller location).
- Re-encodes to WebP at <=1600px, targeting ~300KB regardless of input.
- Enforces the 5MB raw upload cap.
- Stores in the database via ImageData (persistent, survives restarts).
"""

import io

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from ..config import settings


def process_image(raw: bytes) -> bytes:
    """Validate + re-encode image bytes, strips EXIF; returns WebP bytes."""
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds the 5MB limit")
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Empty file")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File is not a valid image") from None
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((settings.max_image_dimension, settings.max_image_dimension))

    for quality in (80, 70, 60, 50, 40):
        buf = io.BytesIO()
        try:
            img.save(buf, format="WEBP", quality=quality, method=4)
        except OSError:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        if buf.tell() <= settings.target_image_bytes or quality == 40:
            return buf.getvalue()
    return buf.getvalue()
