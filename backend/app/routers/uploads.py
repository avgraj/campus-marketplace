"""Image upload route (plan §7, §9)."""

from fastapi import APIRouter, Depends, Request, UploadFile

from ..deps import csrf_check, get_verified_member
from ..models import User
from ..rate_limit import UPLOAD_LIMIT, limiter
from ..schemas import UploadOut
from ..services.images import process_image_upload

router = APIRouter(tags=["uploads"])


@router.post("/uploads/image", response_model=UploadOut)
@limiter.limit(UPLOAD_LIMIT)
def upload_image(
    request: Request,
    file: UploadFile,
    user: User = Depends(get_verified_member),
    _: None = Depends(csrf_check),
):
    return UploadOut(url=process_image_upload(file))
