"""Telegram Bot API helpers (plan §4): community-membership check."""

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
