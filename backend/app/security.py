"""OTP login codes + opaque session tokens.

There are no passwords anywhere in this system — identity comes from
Telegram: the bot DMs a one-time code to the account the user claims,
so entering it proves control of that Telegram account.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .config import settings
from .models import Session, User, utcnow


def generate_login_code() -> str:
    """A 6-digit code, cryptographically random."""
    return f"{secrets.randbelow(900000) + 100000}"


def hash_login_code(code: str) -> str:
    """HMAC with the server secret so a DB leak doesn't expose active codes."""
    return hmac.new(settings.session_secret.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_login_code(code: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_login_code(code), expected_hash)


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
