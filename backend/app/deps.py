"""Shared FastAPI dependencies: session auth, role gates, CSRF header check."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as OrmSession

from .database import get_db
from .models import User
from .security import get_user_for_token

SESSION_COOKIE = "session"


def get_current_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE, "")
    user = get_user_for_token(db, token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return user


def get_verified_member(user: User = Depends(get_current_user)) -> User:
    """Listing creation / contact are gated on community membership, not just
    being logged in (plan §4)."""
    if not user.is_verified_member:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community Telegram group to do this",
        )
    return user


def get_admin(user: User = Depends(get_current_user)) -> User:
    # Checked server-side on every request — never trust a client flag (plan §11).
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admins only")
    return user


def csrf_check(request: Request) -> None:
    """Cheap CSRF defense-in-depth on top of SameSite cookies (plan §11):
    state-changing requests must carry a custom header, which browsers refuse
    to send cross-origin without a CORS preflight we would reject."""
    if request.headers.get("x-requested-with", "").lower() != "fetch":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Missing X-Requested-With header")
