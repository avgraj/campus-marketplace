"""Webhook endpoint for the Telegram bot — receives updates when users
press Start. We record the username → telegram_id mapping so the OTP
login can find them (bots can't resolve @usernames to IDs on their own)."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from ..config import settings
from ..database import get_db
from ..models import Listing, User
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

    # Contact deep link: /start contact_<listing_id>
    parts = text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("contact_"):
        try:
            listing_id = int(parts[1].replace("contact_", ""))
            listing = db.get(Listing, listing_id)
            seller = listing and listing.seller
            if listing and listing.status == "active" and seller and seller.telegram_username:
                contact_text = f'Hi! I am interested in your listing "{listing.title}" (₹{listing.price}) on Campus Marketplace \u2014 is it still available?'
                link = f"https://t.me/{seller.telegram_username}?text={quote(contact_text)}"
                telegram_service.send_message(
                    telegram_id,
                    f"Contact seller for: {listing.title} (₹{listing.price})\n\n"
                    f"Tap to message @{seller.telegram_username}:\n{link}\n\n"
                    f"Or copy this:\n{contact_text}",
                )
                return {"ok": True}
        except (ValueError, AttributeError):
            pass

    telegram_service.send_message(
        telegram_id,
        f"✅ You're registered for {settings.community_name} Marketplace. "
        "Now go back to the website and log in with your Telegram username.",
    )
    return {"ok": True}
