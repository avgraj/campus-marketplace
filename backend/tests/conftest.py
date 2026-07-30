"""Test fixtures. Environment is configured BEFORE any app module is imported,
so the app picks up a throwaway SQLite DB, a temp upload dir, disabled rate
limiting, and DEV_MODE for password-less logins."""

import hashlib
import hmac
import io
import os
import tempfile
import time
from pathlib import Path

import pytest
from PIL import Image

_tmp = tempfile.mkdtemp(prefix="cm-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(Path(_tmp) / "uploads")
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["DEV_MODE"] = "true"
os.environ["COMMUNITY_NAME"] = "Test Campus"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CSRF = {"X-Requested-With": "fetch"}
TEST_BOT_TOKEN = "123456:test-bot-token"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def dev_login(client: TestClient, username: str = "alice", as_admin: bool = False) -> dict:
    r = client.post("/auth/dev-login", json={"username": username, "as_admin": as_admin})
    assert r.status_code == 200, r.text
    return r.json()


def make_png_bytes(color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


def upload_image(client: TestClient) -> str:
    r = client.post(
        "/uploads/image",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
        headers=CSRF,
    )
    assert r.status_code == 200, r.text
    return r.json()["url"]


def create_listing(client: TestClient, title: str = "Vintage Study Table", price: float = 1200.0, **overrides):
    category_id = overrides.pop("category_id", client.get("/categories").json()[0]["id"])
    payload = {
        "title": title,
        "description": overrides.pop(
            "description", "A sturdy table in great condition, pickup from hostel block B."
        ),
        "price": price,
        "category_id": category_id,
        "condition": overrides.pop("condition", "used"),
        "is_negotiable": overrides.pop("is_negotiable", True),
        "image_urls": overrides.pop("image_urls", [upload_image(client)]),
    }
    payload.update(overrides)
    return client.post("/listings", json=payload, headers=CSRF)


def sign_telegram_payload(payload: dict, token: str = TEST_BOT_TOKEN) -> dict:
    """Sign a payload exactly like Telegram would (mirrors plan §3 algorithm)."""
    data = {k: v for k, v in payload.items() if v is not None}
    data.setdefault("auth_date", int(time.time()))
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(token.encode()).digest()
    data["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return data
