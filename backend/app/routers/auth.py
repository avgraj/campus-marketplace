"""Auth routes (plan §3, §4, §9)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from ..config import settings
from ..database import get_db
from ..deps import SESSION_COOKIE, get_current_user
from ..models import User, utcnow
from ..rate_limit import AUTH_LIMIT, limiter
from ..schemas import DevLoginIn, TelegramAuthPayload, UserOut
from ..security import (
    create_session,
    destroy_session,
    get_user_for_token,
    verify_telegram_login,
)
from ..services.telegram import check_community_membership

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,  # not readable from JS — blocks XSS token theft
        secure=settings.cookie_secure,  # True in production (HTTPS)
        # SameSite=None is required for a cross-site prod setup (Vercel →
        # Render) and browsers then mandate Secure. Lax for same-site dev.
        samesite="none" if settings.cookie_secure else "lax",
    )


def _issue_session(request: Request, response: Response, db: OrmSession, user: User) -> UserOut:
    user.last_login_at = utcnow()
    db.commit()
    token = create_session(
        db,
        user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/telegram/callback", response_model=UserOut)
@limiter.limit(AUTH_LIMIT)  # cheap insurance vs junk-payload hammering (plan §11)
def telegram_callback(
    request: Request,
    response: Response,
    payload: TelegramAuthPayload,
    db: OrmSession = Depends(get_db),
):
    if not settings.telegram_bot_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram login is not configured")

    data = payload.model_dump(exclude_none=True)
    # Server-side verification on EVERY callback — never trust the client (plan §11).
    if not verify_telegram_login(data, settings.telegram_bot_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram login payload")

    user = db.scalar(select(User).where(User.telegram_id == payload.id))
    if user is None:
        user = User(telegram_id=payload.id, first_name=payload.first_name)
        db.add(user)
    # Upsert keyed on the numeric telegram_id — usernames can change (plan §3.5).
    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.telegram_username = payload.username
    user.photo_url = payload.photo_url

    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This account is banned")

    # Second trust layer: membership in the community group (plan §4).
    user.is_verified_member = check_community_membership(payload.id)
    db.commit()
    return _issue_session(request, response, db, user)


@router.post("/dev-login", response_model=UserOut)
def dev_login(
    request: Request,
    response: Response,
    payload: DevLoginIn,
    db: OrmSession = Depends(get_db),
):
    """Password-less login for local development/demo — only exists when
    DEV_MODE=true, which must never be true in production."""
    if not settings.dev_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    # Dev users live in a reserved telegram_id range, far from real IDs.
    pseudo_id = -(abs(hash(payload.username)) % 1_000_000) - 1
    user = db.scalar(select(User).where(User.telegram_id == pseudo_id))
    if user is None:
        user = User(telegram_id=pseudo_id, first_name=payload.first_name)
        db.add(user)
    user.telegram_username = payload.username
    user.first_name = payload.first_name
    user.is_verified_member = True  # dev mode skips the Telegram group check
    if payload.as_admin:
        user.is_admin = True
    db.commit()
    return _issue_session(request, response, db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: OrmSession = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        destroy_session(db, token)  # revoking = deleting a row (plan §3.6)
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/session-check")
def session_check(request: Request, db: OrmSession = Depends(get_db)):
    """Lightweight probe: is there a valid session? (no 401, used by the SPA)"""
    user = get_user_for_token(db, request.cookies.get(SESSION_COOKIE, ""))
    return {"logged_in": user is not None}
