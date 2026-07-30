"""Server-side image pipeline (plan §7) — never trust the client.

- Confirms the bytes are really an image (Pillow), not just a .jpg filename.
- Strips EXIF metadata (phone GPS coordinates would leak seller location).
- Re-encodes to WebP at <=1600px, targeting ~300KB regardless of input.
- Enforces the 5MB raw upload cap.
- Stores in Supabase Storage (persistent) or local disk (ephemeral fallback).
"""

import io
import secrets
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from ..config import settings


def _encode(img: Image.Image) -> bytes:
    """Re-encode at decreasing quality until under the target size."""
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


def _process_raw(raw: bytes) -> bytes:
    """Validate image bytes, strip EXIF, re-encode; returns processed bytes."""
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
    return _encode(img)


def _upload_supabase(data: bytes, filename: str) -> str:
    """Upload to Supabase Storage; returns the public URL."""
    url = f"{settings.storage_bucket_url}/object/{settings.storage_bucket}/{filename}"
    resp = httpx.post(
        url,
        content=data,
        headers={
            "Authorization": f"Bearer {settings.storage_api_key}",
            "Content-Type": "image/webp",
        },
        timeout=30,
    )
    if not resp.is_success:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image to storage ({resp.status_code})",
        )
    return f"{settings.storage_bucket_url}/object/public/{settings.storage_bucket}/{filename}"


def process_image_upload(file: UploadFile) -> str:
    """Validate + process an uploaded image; returns the public URL."""
    raw = file.file.read(settings.max_upload_bytes + 1)
    data = _process_raw(raw)
    filename = f"{secrets.token_hex(16)}.webp"

    if settings.storage_bucket_url and settings.storage_api_key:
        return _upload_supabase(data, filename)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(data)
    return f"/uploads/{filename}"
