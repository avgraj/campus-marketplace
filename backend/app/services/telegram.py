"""Telegram Bot API helpers: community-membership check + DM delivery."""

import httpx

from ..config import settings

ACCEPTED_STATUSES = {"member", "administrator", "creator"}


def check_community_membership(telegram_user_id: int) -> bool:
    """True if the user is in the community group/channel.

    If no COMMUNITY_GROUP_CHAT_ID is configured (local dev), the check is
    skipped and everyone passes — set it in production.
    """
    if not settings.community_group_chat_id or not settings.telegram_bot_token:
        return True
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getChatMember"
    try:
        resp = httpx.get(
            url,
            params={"chat_id": settings.community_group_chat_id, "user_id": telegram_user_id},
            timeout=10,
        )
        body = resp.json()
    except Exception:
        return False  # fail closed: can't confirm membership → don't grant it
    if not body.get("ok"):
        return False
    return body.get("result", {}).get("status") in ACCEPTED_STATUSES


def send_message(telegram_user_id: int, text: str) -> bool:
    """DM a user from the bot. Returns False if delivery fails — most often
    because the user has never pressed Start on the bot (Telegram forbids
    bots from messaging strangers first)."""
    if not settings.telegram_bot_token:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        resp = httpx.post(url, json={"chat_id": telegram_user_id, "text": text}, timeout=10)
        return bool(resp.json().get("ok"))
    except Exception:
        return False


def send_login_code(telegram_user_id: int, code: str) -> bool:
    text = (
        f"Your {settings.community_name} Marketplace login code: {code}\n\n"
        f"Valid for {settings.login_code_ttl_minutes} minutes, single use. "
        "If you didn't request it, ignore this message."
    )
    return send_message(telegram_user_id, text)
