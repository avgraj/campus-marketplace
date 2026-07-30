"""Admin/moderation routes (plan §9, §12). Every route re-checks is_admin
server-side via the get_admin dependency."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession, selectinload

from ..database import get_db
from ..deps import csrf_check, get_admin
from ..models import Listing, Report, User
from ..schemas import ReportOut
from ..security import destroy_user_sessions

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin), Depends(csrf_check)],
)


@router.get("/reports", response_model=list[ReportOut])
def moderation_queue(db: OrmSession = Depends(get_db)):
    reports = db.scalars(
        select(Report)
        .where(Report.status == "pending")
        .options(
            selectinload(Report.listing).selectinload(Listing.images),
            selectinload(Report.listing).selectinload(Listing.category),
            selectinload(Report.reporter),
        )
        .order_by(Report.created_at.asc())
    ).all()
    return [ReportOut.model_validate(r) for r in reports]


@router.post("/reports/{report_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_report(report_id: int, db: OrmSession = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    report.status = "dismissed"
    db.commit()


@router.post("/listings/{listing_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
def remove_listing(listing_id: int, db: OrmSession = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing not found")
    listing.status = "removed"
    # Resolving the listing resolves its pending reports too.
    for report in db.scalars(select(Report).where(Report.listing_id == listing.id, Report.status == "pending")):
        report.status = "reviewed"
    db.commit()


@router.post("/users/{user_id}/ban", status_code=status.HTTP_204_NO_CONTENT)
def ban_user(user_id: int, admin: User = Depends(get_admin), db: OrmSession = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="You cannot ban yourself")
    user.is_banned = True
    destroy_user_sessions(db, user.id)  # ban takes effect immediately (plan §12)
    db.commit()
