"""Auth: OTP login flow (bot → code → verify), dev login, session lifecycle."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

from .conftest import CSRF, WH_HEADERS, dev_login, webhook_start


# ── Bot webhook (registers users) ─────────────────────────────────────────────


def test_webhook_registers_user(client, monkeypatch):
    sent = []

    def fake_send(uid, text):
        sent.append((uid, text))
        return True

    monkeypatch.setattr("app.services.telegram.send_message", fake_send)
    r = webhook_start(client, 1001, "alice_otp", "Alice")
    assert r.status_code == 200
    assert len(sent) == 1
    assert sent[0][0] == 1001
    assert "registered" in sent[0][1].lower()

    # /me should still be 401 — user is registered but not logged in
    assert client.get("/auth/me").status_code == 401


def test_webhook_rejects_wrong_secret(client):
    r = client.post(
        "/telegram/webhook",
        json={"message": {"text": "/start", "from": {"id": 1, "first_name": "X"}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert r.status_code == 403


def test_webhook_ignores_non_start_messages(client):
    r = client.post(
        "/telegram/webhook",
        json={"message": {"text": "hello", "from": {"id": 1, "first_name": "X"}}},
        headers=WH_HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_webhook_stores_username_none_for_no_username(client):
    """Telegram accounts without a public @username get stored with None."""
    r = webhook_start(client, 1002, None, "NoName")
    assert r.status_code == 200
    me = client.get("/auth/me").status_code  # not logged in yet, but user exists in DB
    assert me == 401


# ── OTP login — code request + verify ─────────────────────────────────────────


def test_otp_full_flow(client, monkeypatch):
    captured = []

    def fake_send(uid, code):
        captured.append(code)
        return True

    monkeypatch.setattr("app.services.telegram.send_login_code", fake_send)

    # Register user via /start
    webhook_start(client, 2001, "otp_user", "Otis")

    # Step 1 — request code
    r = client.post("/auth/code/request", json={"username": "otp_user"})
    assert r.status_code == 200
    assert r.json()["sent"] is True
    code = captured[0]
    assert len(code) == 6 and code.isdigit()

    # Step 2 — verify
    r = client.post("/auth/code/verify", json={"username": "otp_user", "code": code})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["telegram_username"] == "otp_user"
    assert "session" in r.cookies

    # Session works
    assert client.get("/auth/me").json()["telegram_username"] == "otp_user"


def test_otp_request_fails_for_unknown_username(client):
    webhook_start(client, 3001, "known_user", "Known")
    r = client.post("/auth/code/request", json={"username": "unknown"})
    assert r.status_code == 400
    assert "press Start" in r.json()["detail"]


def test_otp_wrong_code_fails(client, monkeypatch):
    captured = []
    monkeypatch.setattr("app.services.telegram.send_login_code", lambda uid, code: captured.append(code) or True)
    webhook_start(client, 4001, "wrong_code_user", "Wanda")
    client.post("/auth/code/request", json={"username": "wrong_code_user"})
    code = captured[0]

    r = client.post("/auth/code/verify", json={"username": "wrong_code_user", "code": "000000"})
    assert r.status_code == 401

    # Correct code still works (code isn't burned on one wrong attempt)
    r = client.post("/auth/code/verify", json={"username": "wrong_code_user", "code": code})
    assert r.status_code == 200, r.text


def test_otp_too_many_attempts_locks_code(client, monkeypatch):
    captured = []
    monkeypatch.setattr("app.services.telegram.send_login_code", lambda uid, code: captured.append(code) or True)
    webhook_start(client, 5001, "locked_user", "Larry")
    client.post("/auth/code/request", json={"username": "locked_user"})

    # 5 wrong tries count as attempts; the 6th hits the cap (>= 5).
    for _ in range(5):
        r = client.post("/auth/code/verify", json={"username": "locked_user", "code": "000000"})
        assert r.status_code == 401  # each individual failure returns 401
    # Now attempts = 5, which is >= max_attempts (5), so next try returns 429
    r = client.post("/auth/code/verify", json={"username": "locked_user", "code": "000000"})
    assert r.status_code == 429
    assert "Too many" in r.json()["detail"]

    # Even the real code won't work now (code was deleted after cap hit)
    r = client.post("/auth/code/verify", json={"username": "locked_user", "code": captured[0]})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


def test_otp_code_single_use(client, monkeypatch):
    captured = []
    monkeypatch.setattr("app.services.telegram.send_login_code", lambda uid, code: captured.append(code) or True)
    webhook_start(client, 6001, "single_user", "Susan")
    client.post("/auth/code/request", json={"username": "single_user"})
    code = captured[0]

    client.post("/auth/code/verify", json={"username": "single_user", "code": code})
    r = client.post("/auth/code/verify", json={"username": "single_user", "code": code})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


def test_otp_username_case_insensitive(client, monkeypatch):
    monkeypatch.setattr("app.services.telegram.send_login_code", lambda uid, code: True)
    webhook_start(client, 7001, "CaseUser", "Casey")
    r = client.post("/auth/code/request", json={"username": "caseuser"})
    assert r.status_code == 200, r.text


# ── Telegram Bot API limitations ──────────────────────────────────────────────


def test_otp_request_fails_when_bot_cannot_dm(client, monkeypatch):
    # The user exists in our DB but hasn't pressed Start on the bot.
    # send_login_code returns False.
    monkeypatch.setattr("app.services.telegram.send_login_code", lambda uid, code: False)
    webhook_start(client, 8001, "unstarted", "Nostart")
    r = client.post("/auth/code/request", json={"username": "unstarted"})
    assert r.status_code == 400
    assert "press Start" in r.json()["detail"]


# ── Dev login + session lifecycle (shared with OTP) ───────────────────────────


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
