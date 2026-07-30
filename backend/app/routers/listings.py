"""Listing routes (plan §6, §8, §9)."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as OrmSession, selectinload

from ..config import BLOCKED_KEYWORDS, settings
from ..database import get_db
from ..deps import SESSION_COOKIE, csrf_check, get_current_user, get_verified_member
from ..models import Category, Listing, ListingImage, Report, User, utcnow
from ..rate_limit import READ_LIMIT, WRITE_LIMIT, limiter
from ..schemas import (
    ListingCardOut,
    ListingCreate,
    ListingDetailOut,
    ListingPageOut,
    ListingUpdate,
    ReportCreate,
    SellerOut,
)
from ..security import get_user_for_token

router = APIRouter(tags=["listings"])


def _check_blocked_content(title: str, description: str) -> None:
    """Prohibited-keyword enforcement at creation, with a clear rejection
    message rather than a silent drop (plan §12)."""
    haystack = f"{title} {description}".lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in haystack:
            raise HTTPException(
                status_code=422,
                detail=f"Listing rejected: contains prohibited content ('{keyword}')",
            )


def _visible_public_clause():
    return (Listing.status == "active") & (Listing.expires_at > utcnow())


def _eager_query():
    return select(Listing).options(selectinload(Listing.images), selectinload(Listing.category))


# ── Browse / search (public) ──────────────────────────────────────────────────


@router.get("/listings", response_model=ListingPageOut)
@limiter.limit(READ_LIMIT)
def browse_listings(
    request: Request,
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, description="category slug"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    condition: str | None = Query(default=None),
    sort: str = Query(default="newest", pattern="^(newest|price_asc|price_desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: OrmSession = Depends(get_db),
):
    filters = [_visible_public_clause()]
    if q:
        # Portable full-text-ish search (ILIKE) — works on SQLite and Postgres.
        # On Postgres at scale, swap for the tsvector column from plan §5.
        like = f"%{q.strip()}%"
        filters.append(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if category:
        filters.append(Listing.category.has(Category.slug == category))
    if min_price is not None:
        filters.append(Listing.price >= min_price)
    if max_price is not None:
        filters.append(Listing.price <= max_price)
    if condition:
        filters.append(Listing.condition == condition)

    total = db.scalar(select(func.count()).select_from(Listing).where(*filters)) or 0

    order = {
        "newest": Listing.created_at.desc(),
        "price_asc": Listing.price.asc(),
        "price_desc": Listing.price.desc(),
    }[sort]
    items = db.scalars(
        _eager_query().where(*filters).order_by(order).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ListingPageOut(
        items=[ListingCardOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# Declared BEFORE /listings/{id} so "mine" isn't captured by the int route.
@router.get("/listings/mine", response_model=list[ListingCardOut])
def my_listings(user: User = Depends(get_current_user), db: OrmSession = Depends(get_db)):
    items = db.scalars(
        _eager_query()
        .where(Listing.seller_id == user.id, Listing.status != "removed")
        .order_by(Listing.created_at.desc())
    ).all()
    return [ListingCardOut.model_validate(i) for i in items]


@router.get("/listings/{listing_id}", response_model=ListingDetailOut)
def listing_detail(listing_id: int, request: Request, db: OrmSession = Depends(get_db)):
    listing = db.scalar(_eager_query().where(Listing.id == listing_id))
    requester = get_user_for_token(db, request.cookies.get(SESSION_COOKIE, ""))
    is_privileged = requester is not None and (requester.is_admin or requester.id == listing.seller_id if listing else False)

    if listing is None or listing.status == "removed":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing not found")
    is_public = listing.status in ("active", "sold") and not (
        listing.status == "active" and listing.expires_at <= utcnow()
    )
    if not is_public and not is_privileged:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing not found")

    out = ListingDetailOut.model_validate(listing)
    out.is_mine = requester is not None and requester.id == listing.seller_id
    # Gate the seller's username behind login (plan §8): anonymous visitors
    # can browse, but contact info only goes to the community.
    out.seller = SellerOut(
        first_name=listing.seller.first_name,
        telegram_username=listing.seller.telegram_username if requester else None,
    )
    return out


# ── Create / edit / lifecycle ─────────────────────────────────────────────────


@router.post("/listings", response_model=ListingDetailOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(WRITE_LIMIT)
def create_listing(
    request: Request,
    payload: ListingCreate,
    user: User = Depends(get_verified_member),
    db: OrmSession = Depends(get_db),
    _: None = Depends(csrf_check),
):
    # No username → buyers have no way to reach this seller (plan §7/§8).
    if not user.telegram_username:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Set a Telegram username in your Telegram app before publishing — buyers contact you via t.me/<username>",
        )

    _check_blocked_content(payload.title, payload.description)

    # Anti-spam caps (plan §6): even verified accounts can't flood the feed.
    active_count = db.scalar(
        select(func.count()).select_from(Listing).where(
            Listing.seller_id == user.id, Listing.status == "active"
        )
    ) or 0
    if active_count >= settings.max_active_listings_per_user:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Active-listing limit reached (10)")
    day_ago = utcnow() - timedelta(days=1)
    today_count = db.scalar(
        select(func.count()).select_from(Listing).where(
            Listing.seller_id == user.id, Listing.created_at > day_ago
        )
    ) or 0
    if today_count >= settings.max_listings_per_day:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily listing limit reached (5/day)")

    category = db.get(Category, payload.category_id)
    if category is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown category")

    listing = Listing(
        seller_id=user.id,
        category_id=category.id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        is_negotiable=payload.is_negotiable,
        condition=payload.condition,
    )
    db.add(listing)
    db.flush()  # get listing.id before attaching images
    for position, url in enumerate(payload.image_urls):
        db.add(ListingImage(listing_id=listing.id, url=url, position=position))
    db.commit()
    db.refresh(listing)

    out = ListingDetailOut.model_validate(listing)
    out.is_mine = True
    out.seller = SellerOut(first_name=user.first_name, telegram_username=user.telegram_username)
    return out


def _get_own_listing(listing_id: int, user: User, db: OrmSession) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status == "removed":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.seller_id != user.id and not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your listing")
    return listing


@router.put("/listings/{listing_id}", response_model=ListingDetailOut)
@limiter.limit(WRITE_LIMIT)
def update_listing(
    request: Request,
    listing_id: int,
    payload: ListingUpdate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
    _: None = Depends(csrf_check),
):
    listing = _get_own_listing(listing_id, user, db)
    data = payload.model_dump(exclude_unset=True)

    new_title = data.get("title", listing.title)
    new_description = data.get("description", listing.description)
    _check_blocked_content(new_title, new_description)

    if "category_id" in data and db.get(Category, data["category_id"]) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown category")

    image_urls = data.pop("image_urls", None)
    for field, value in data.items():
        setattr(listing, field, value)
    if image_urls is not None:
        for img in list(listing.images):
            db.delete(img)
        db.flush()
        for position, url in enumerate(image_urls):
            db.add(ListingImage(listing_id=listing.id, url=url, position=position))
    db.commit()
    db.refresh(listing)

    out = ListingDetailOut.model_validate(listing)
    out.is_mine = True
    out.seller = SellerOut(first_name=user.first_name, telegram_username=user.telegram_username)
    return out


@router.post("/listings/{listing_id}/mark-sold", response_model=ListingCardOut)
def mark_sold(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
    _: None = Depends(csrf_check),
):
    listing = _get_own_listing(listing_id, user, db)
    listing.status = "sold"
    db.commit()
    db.refresh(listing)
    return ListingCardOut.model_validate(listing)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
    _: None = Depends(csrf_check),
):
    # Soft delete — owner or admin (plan §9).
    listing = _get_own_listing(listing_id, user, db)
    listing.status = "removed"
    db.commit()


@router.post("/listings/{listing_id}/report", status_code=status.HTTP_201_CREATED)
@limiter.limit(WRITE_LIMIT)
def report_listing(
    request: Request,
    listing_id: int,
    payload: ReportCreate,
    user: User = Depends(get_current_user),
    db: OrmSession = Depends(get_db),
    _: None = Depends(csrf_check),
):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status == "removed":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Listing not found")
    db.add(Report(listing_id=listing.id, reported_by=user.id, reason=payload.reason))
    db.commit()
    return {"ok": True}
