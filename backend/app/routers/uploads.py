"""Image upload route (plan §7, §9) + serve endpoint for DB-stored images."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session as OrmSession

from ..database import get_db
from ..deps import csrf_check, get_verified_member
from ..models import ImageData, User
from ..rate_limit import UPLOAD_LIMIT, limiter
from ..schemas import UploadOut
from ..services.images import process_image

router = APIRouter(tags=["uploads"])


@router.post("/uploads/image", response_model=UploadOut)
@limiter.limit(UPLOAD_LIMIT)
def upload_image(
    request: Request,
    file: UploadFile,
    user: User = Depends(get_verified_member),
    _: None = Depends(csrf_check),
    db: OrmSession = Depends(get_db),
):
    raw = file.file.read()
    data = process_image(raw)
    img = ImageData(data=data)
    db.add(img)
    db.commit()
    return UploadOut(url=f"/image/{img.id}")


@router.get("/image/{image_id}")
def serve_image(image_id: int, db: OrmSession = Depends(get_db)):
    img = db.get(ImageData, image_id)
    if not img:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    return Response(content=img.data, media_type="image/webp")
