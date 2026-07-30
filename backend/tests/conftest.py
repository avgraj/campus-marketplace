"""Test fixtures. Environment is configured BEFORE any app module is imported,
so the app picks up a throwaway SQLite DB, a temp upload dir, disabled rate
limiting, and DEV_MODE for password-less logins."""

import io
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image

_tmp = tempfile.mkdtemp(prefix="cm-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(Path(_tmp) / "uploads")
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["DEV_MODE"] = "true"
os.environ["COMMUNITY_NAME"] = "Test Campus"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "wh-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CSRF = {"X-Requested-With": "fetch"}
WH_SECRET = "wh-secret"
WH_HEADERS = {"X-Telegram-Bot-Api-Secret-Token": WH_SECRET}


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


def webhook_start(client: TestClient, telegram_id: int, username: str | None = None, first_name: str = "TestUser"):
    """Simulate a Telegram user pressing /start on the bot."""
    payload = {
        "message": {
            "text": "/start",
            "from": {"id": telegram_id, "first_name": first_name, "username": username or None},
        }
    }
    return client.post("/telegram/webhook", json=payload, headers=WH_HEADERS)
