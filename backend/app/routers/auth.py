"""Auth routes: bot-delivered OTP login, dev login, session lifecycle."""

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as OrmSession

from ..config import settings
from ..database import get_db
from ..deps import SESSION_COOKIE, get_current_user
from ..models import LoginCode, User, utcnow
from ..rate_limit import AUTH_LIMIT, limiter
from ..schemas import CodeRequestIn, CodeVerifyIn, DevLoginIn, UserOut
from ..security import (
    create_session,
    destroy_session,
    generate_login_code,
    get_user_for_token,
    hash_login_code,
    verify_login_code,
)
from ..services import telegram as telegram_service

router = APIRouter(prefix="/auth", tags=["auth"])

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


def _normalize_username(raw: str) -> str:
    username = raw.strip().lstrip("@").lower()
    if not _USERNAME_RE.match(username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Enter a valid Telegram username (5–32 letters, digits, _)")
    return username


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


# ── OTP login ─────────────────────────────────────────────────────────────────
#
# Step 0 (once, in Telegram): open the bot and press Start — Telegram forbids
# bots from messaging users first, and usernames can't be resolved to IDs by
# the Bot API. The /start webhook stores username → telegram_id.
# Step 1: POST /auth/code/request  → bot DMs a 6-digit code to that account.
# Step 2: POST /auth/code/verify   → proves control of the account → session.


@router.post("/code/request")
@limiter.limit(AUTH_LIMIT)
def request_code(
    request: Request,
    payload: CodeRequestIn,
    db: OrmSession = Depends(get_db),
):
    username = _normalize_username(payload.username)
    user = db.scalar(
        select(User).where(func.lower(User.telegram_username) == username)
    )
    if user is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"We don't know @{username} yet — open @{settings.telegram_bot_username} in Telegram and press Start, then try again",
        )
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This account is banned")

    # One active code per account — requesting a new one invalidates the old.
    db.execute(delete(LoginCode).where(LoginCode.telegram_id == user.telegram_id))
    code = generate_login_code()
    db.add(
        LoginCode(
            telegram_id=user.telegram_id,
            code_hash=hash_login_code(code),
            expires_at=utcnow() + timedelta(minutes=settings.login_code_ttl_minutes),
        )
    )
    db.commit()

    if not telegram_service.send_login_code(user.telegram_id, code):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Couldn't message you — open @{settings.telegram_bot_username} in Telegram and press Start, then try again",
        )
    return {"sent": True}


@router.post("/code/verify", response_model=UserOut)
@limiter.limit(AUTH_LIMIT)
def verify_code(
    request: Request,
    response: Response,
    payload: CodeVerifyIn,
    db: OrmSession = Depends(get_db),
):
    username = _normalize_username(payload.username)
    user = db.scalar(
        select(User).where(func.lower(User.telegram_username) == username)
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid username or code")

    login_code = db.scalar(
        select(LoginCode)
        .where(LoginCode.telegram_id == user.telegram_id)
        .order_by(LoginCode.id.desc())
        .limit(1)
    )
    if login_code is None or login_code.expires_at <= utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Code expired — request a new one")
    if login_code.attempts >= settings.login_code_max_attempts:
        db.execute(delete(LoginCode).where(LoginCode.telegram_id == user.telegram_id))
        db.commit()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many wrong attempts — request a new code",
        )

    if not verify_login_code(payload.code, login_code.code_hash):
        login_code.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid username or code")

    # Success — burn every outstanding code for this account (single use).
    db.execute(delete(LoginCode).where(LoginCode.telegram_id == user.telegram_id))
    if user.is_banned:
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This account is banned")

    # Second trust layer: membership in the community group.
    user.is_verified_member = telegram_service.check_community_membership(user.telegram_id)
    db.commit()
    return _issue_session(request, response, db, user)


# ── Dev login (DEV_MODE only) ─────────────────────────────────────────────────


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


# ── Session lifecycle ─────────────────────────────────────────────────────────


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: OrmSession = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        destroy_session(db, token)  # revoking = deleting a row
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/session-check")
def session_check(request: Request, db: OrmSession = Depends(get_db)):
    """Lightweight probe: is there a valid session? (no 401, used by the SPA)"""
    user = get_user_for_token(db, request.cookies.get(SESSION_COOKIE, ""))
    return {"logged_in": user is not None}
