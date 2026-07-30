"""Webhook endpoint for the Telegram bot — receives updates when users
press Start. We record the username → telegram_id mapping so the OTP
login can find them (bots can't resolve @usernames to IDs on their own)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from ..config import settings
from ..database import get_db
from ..models import User
from ..services import telegram as telegram_service

router = APIRouter(tags=["telegram"])


@router.post("/telegram/webhook", status_code=status.HTTP_200_OK)
def telegram_webhook(
    request: Request,
    update: dict,
    db: OrmSession = Depends(get_db),
):
    # Verify secret token if configured (setWebhook secret_token).
    if settings.telegram_webhook_secret:
        actual = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if actual != settings.telegram_webhook_secret:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bad secret token")

    msg = update.get("message") or {}
    text = msg.get("text", "")
    if not text.startswith("/start"):
        return {"ok": True}

    from_user = msg.get("from") or {}
    telegram_id = from_user.get("id")
    if not telegram_id:
        return {"ok": True}

    first_name = from_user.get("first_name", "User")
    last_name = from_user.get("last_name")
    username = from_user.get("username")  # None if user has no @username

    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, first_name=first_name)
        db.add(user)
    user.first_name = first_name
    user.last_name = last_name
    user.telegram_username = username
    db.commit()

    telegram_service.send_message(
        telegram_id,
        f"✅ You're registered for {settings.community_name} Marketplace. "
        "Now go back to the website and log in with your Telegram username.",
    )
    return {"ok": True}
