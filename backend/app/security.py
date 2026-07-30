"""Telegram login verification + opaque session tokens (plan §3).

There are no passwords anywhere in this system — identity comes from
Telegram, and the HMAC check below is what proves a login payload really
came from Telegram and not from an attacker typing JSON into curl.
"""

import hashlib
import hmac
import secrets
import time
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .config import settings
from .models import Session, User, utcnow

MAX_AUTH_AGE_SECONDS = 86_400  # 24h — reject replayed old logins (plan §3.4)


def verify_telegram_login(data: dict[str, Any], bot_token: str) -> bool:
    """Verify a Telegram Login Widget payload. See plan §3 for the algorithm."""
    data = dict(data)  # don't mutate caller's dict
    received_hash = data.pop("hash", None)
    if not received_hash:
        return False
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, str(received_hash)):
        return False
    try:
        if time.time() - int(data["auth_date"]) > MAX_AUTH_AGE_SECONDS:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: OrmSession, user: User, ip: str | None, user_agent: str | None) -> str:
    """Create a server-side session row; returns the raw opaque token (shown once)."""
    token = secrets.token_urlsafe(32)
    db.add(
        Session(
            id=_hash_token(token),
            user_id=user.id,
            ip_address=ip,
            user_agent=(user_agent or "")[:300],
            expires_at=utcnow() + timedelta(days=settings.session_ttl_days),
        )
    )
    db.commit()
    return token


def get_user_for_token(db: OrmSession, token: str) -> User | None:
    """Resolve a session cookie to a user, or None if invalid/expired/banned."""
    if not token:
        return None
    session = db.scalar(select(Session).where(Session.id == _hash_token(token)))
    if session is None or session.expires_at <= utcnow():
        return None
    user = db.get(User, session.user_id)
    if user is None or user.is_banned:
        return None
    return user


def destroy_session(db: OrmSession, token: str) -> None:
    session = db.scalar(select(Session).where(Session.id == _hash_token(token)))
    if session is not None:
        db.delete(session)
        db.commit()


def destroy_user_sessions(db: OrmSession, user_id: int) -> None:
    """Ban handling: revoke every session the user has (plan §12)."""
    for s in db.scalars(select(Session).where(Session.user_id == user_id)):
        db.delete(s)
    db.commit()
