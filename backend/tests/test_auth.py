"""Auth: Telegram hash verification (plan §3), sessions, dev login."""

import time

from app.config import settings
from app.security import verify_telegram_login

from .conftest import CSRF, TEST_BOT_TOKEN, dev_login, sign_telegram_payload


# ── Pure verification logic ───────────────────────────────────────────────────


def test_verify_accepts_valid_payload():
    payload = sign_telegram_payload({"id": 111, "first_name": "Asha", "auth_date": int(time.time())})
    assert verify_telegram_login(payload, TEST_BOT_TOKEN) is True


def test_verify_rejects_tampered_payload():
    payload = sign_telegram_payload({"id": 111, "first_name": "Asha", "auth_date": int(time.time())})
    payload["first_name"] = "Mallory"  # tamper after signing
    assert verify_telegram_login(payload, TEST_BOT_TOKEN) is False


def test_verify_rejects_wrong_token():
    payload = sign_telegram_payload({"id": 111, "first_name": "Asha", "auth_date": int(time.time())})
    assert verify_telegram_login(payload, "999:different-token") is False


def test_verify_rejects_stale_auth_date():
    payload = sign_telegram_payload(
        {"id": 111, "first_name": "Asha", "auth_date": int(time.time()) - 90000}  # 25h old
    )
    assert verify_telegram_login(payload, TEST_BOT_TOKEN) is False


def test_verify_rejects_missing_hash():
    assert verify_telegram_login({"id": 1, "auth_date": int(time.time())}, TEST_BOT_TOKEN) is False


# ── Telegram callback endpoint (end-to-end with monkeypatched bot token) ──────


def test_telegram_callback_creates_user_and_session(client, monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", TEST_BOT_TOKEN)
    payload = sign_telegram_payload({"id": 424242, "first_name": "Ravi", "username": "ravi_k"})
    r = client.post("/auth/telegram/callback", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["telegram_username"] == "ravi_k"
    assert "session" in r.cookies  # HttpOnly session cookie issued

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["first_name"] == "Ravi"


def test_telegram_callback_rejects_bad_hash(client, monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", TEST_BOT_TOKEN)
    payload = sign_telegram_payload({"id": 424243, "first_name": "Ravi"})
    payload["hash"] = "0" * 64
    r = client.post("/auth/telegram/callback", json=payload)
    assert r.status_code == 401


def test_telegram_callback_unavailable_without_bot_token(client, monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", "")
    r = client.post("/auth/telegram/callback", json={"id": 1, "first_name": "X", "auth_date": 1, "hash": "x"})
    assert r.status_code == 503


# ── Dev login + session lifecycle ─────────────────────────────────────────────


def test_dev_login_me_logout(client):
    user = dev_login(client, "alice")
    assert user["is_verified_member"] is True

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["telegram_username"] == "alice"

    assert client.get("/auth/session-check").json() == {"logged_in": True}

    r = client.post("/auth/logout", headers=CSRF)
    assert r.status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/session-check").json() == {"logged_in": False}


def test_me_requires_login(client):
    assert client.get("/auth/me").status_code == 401


def test_dev_login_disabled_when_dev_mode_off(client, monkeypatch):
    monkeypatch.setattr(settings, "dev_mode", False)
    r = client.post("/auth/dev-login", json={"username": "mallory"})
    assert r.status_code == 404
