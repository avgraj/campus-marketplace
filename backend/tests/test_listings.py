"""Listings: CRUD, search/filters, contact gating, anti-spam, moderation input.

Each test uses a distinct dev username because the anti-spam caps (plan §6)
are per-user and the test DB is shared across the suite."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

from .conftest import CSRF, create_listing, dev_login, sign_telegram_payload, upload_image


def test_categories_seeded(client):
    r = client.get("/categories")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) == 10
    assert {c["slug"] for c in cats} >= {"others", "electronics-gadgets"}


def test_create_and_browse_listing(client):
    dev_login(client, "seller-browse")
    r = create_listing(client, title="Vintage Study Table Zebra")
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["is_mine"] is True
    assert created["seller"]["telegram_username"] == "seller-browse"

    # Public browse finds it (no login needed)
    page = client.get("/listings", params={"q": "Zebra"}).json()
    assert page["total"] == 1
    assert page["items"][0]["title"] == "Vintage Study Table Zebra"
    assert len(page["items"][0]["images"]) == 1


def test_search_filters_and_sort(client):
    dev_login(client, "seller-filters")
    create_listing(client, title="Uniqkeyboard Calculator", price=300)
    create_listing(client, title="Uniqkeyboard Lamp", price=900, condition="new")

    by_q = client.get("/listings", params={"q": "Uniqkeyboard"}).json()
    assert by_q["total"] == 2

    cheap_first = client.get("/listings", params={"q": "Uniqkeyboard", "sort": "price_asc"}).json()
    assert [i["price"] for i in cheap_first["items"]] == [300, 900]

    dear_first = client.get("/listings", params={"q": "Uniqkeyboard", "sort": "price_desc"}).json()
    assert [i["price"] for i in dear_first["items"]] == [900, 300]

    only_new = client.get("/listings", params={"q": "Uniqkeyboard", "condition": "new"}).json()
    assert only_new["total"] == 1

    price_band = client.get("/listings", params={"q": "Uniqkeyboard", "min_price": 500}).json()
    assert price_band["total"] == 1


def test_contact_username_gated_behind_login(client):
    dev_login(client, "seller-gated")
    listing_id = create_listing(client, title="Gatecheck Bicycle").json()["id"]

    # Anonymous: can view the listing, but NOT the seller's username (plan §8)
    with TestClient(app) as anon:
        detail = anon.get(f"/listings/{listing_id}").json()
        assert detail["seller"]["first_name"]
        assert detail["seller"]["telegram_username"] is None

    # Logged in: username is included so the Telegram redirect can be built
    detail = client.get(f"/listings/{listing_id}").json()
    assert detail["seller"]["telegram_username"] == "seller-gated"


def test_publish_requires_telegram_username(client, monkeypatch):
    # A real Telegram account without a public @username (plan §7 edge case)
    monkeypatch.setattr(settings, "telegram_bot_token", "123456:test-bot-token")
    payload = sign_telegram_payload({"id": 777001, "first_name": "NoName"})
    assert client.post("/auth/telegram/callback", json=payload).status_code == 200

    r = create_listing(client, title="Username Guard Test")
    assert r.status_code == 400
    assert "username" in r.json()["detail"].lower()


def test_blocked_keyword_rejected_with_clear_message(client):
    dev_login(client, "seller-blocked")
    r = create_listing(client, title="Selling green weed stuff")
    assert r.status_code == 422
    assert "prohibited" in r.json()["detail"].lower()


def test_validation_rules(client):
    dev_login(client, "seller-validation")
    assert create_listing(client, title="abc").status_code == 422  # title too short
    assert create_listing(client, title="Valid Title Here", description="too short").status_code == 422
    assert create_listing(client, title="Valid Title Here", price=-5).status_code == 422
    assert create_listing(client, title="Valid Title Here", image_urls=[]).status_code == 422
    assert create_listing(client, title="Valid Title Here", image_urls=["https://evil.com/x.jpg"]).status_code == 422


def test_create_requires_login_and_csrf(client):
    category_id = client.get("/categories").json()[0]["id"]
    body = {
        "title": "Boundary Test Listing",
        "description": "A perfectly valid description for boundary testing.",
        "price": 10,
        "category_id": category_id,
        "condition": "used",
        "image_urls": ["/uploads/placeholder.webp"],
    }
    # Not logged in → 401
    assert client.post("/listings", json=body, headers=CSRF).status_code == 401

    # Logged in but missing the CSRF header → 403
    dev_login(client, "seller-csrf")
    assert client.post("/listings", json=body).status_code == 403


def test_edit_mark_sold_delete_lifecycle(client):
    dev_login(client, "seller-lifecycle")
    listing_id = create_listing(client, title="Lifecycle Item One").json()["id"]

    # Edit
    r = client.put(f"/listings/{listing_id}", json={"price": 500, "title": "Lifecycle Item One Updated"}, headers=CSRF)
    assert r.status_code == 200, r.text
    assert r.json()["price"] == 500

    # Mark sold → disappears from public browse
    r = client.post(f"/listings/{listing_id}/mark-sold", headers=CSRF)
    assert r.status_code == 200
    assert r.json()["status"] == "sold"
    assert client.get("/listings", params={"q": "Lifecycle Item One"}).json()["total"] == 0

    # Delete → 404 even for the owner
    assert client.delete(f"/listings/{listing_id}", headers=CSRF).status_code == 204
    assert client.get(f"/listings/{listing_id}").status_code == 404


def test_cannot_edit_others_listing(client):
    dev_login(client, "seller-owner")
    listing_id = create_listing(client, title="Ownership Test Item").json()["id"]

    with TestClient(app) as other:
        dev_login(other, "buyer-not-owner")
        assert other.put(f"/listings/{listing_id}", json={"price": 1}, headers=CSRF).status_code == 403
        assert other.post(f"/listings/{listing_id}/mark-sold", headers=CSRF).status_code == 403
        assert other.delete(f"/listings/{listing_id}", headers=CSRF).status_code == 403


def test_my_listings(client):
    dev_login(client, "seller-mine")
    create_listing(client, title="Mine List Test Alpha")
    mine = client.get("/listings/mine")
    assert mine.status_code == 200
    assert any(i["title"] == "Mine List Test Alpha" for i in mine.json())


def test_daily_creation_cap(client):
    dev_login(client, "seller-capped")  # fresh user, no listings yet
    for i in range(5):
        r = create_listing(client, title=f"Cap Test Item {i}")
        assert r.status_code == 201, r.text
    r = create_listing(client, title="Cap Test Item Six")
    assert r.status_code == 429


def test_report_listing(client):
    dev_login(client, "seller-reported")
    listing_id = create_listing(client, title="Reportable Item X").json()["id"]
    r = client.post(f"/listings/{listing_id}/report", json={"reason": "Looks like a scam"}, headers=CSRF)
    assert r.status_code == 201

    # Anonymous cannot report
    with TestClient(app) as anon:
        assert anon.post(f"/listings/{listing_id}/report", json={"reason": "spam"}, headers=CSRF).status_code == 401


def test_uploaded_image_url_reused_in_listing(client):
    dev_login(client, "seller-upload")
    url = upload_image(client)
    r = create_listing(client, title="Upload Flow Listing", image_urls=[url])
    assert r.status_code == 201, r.text
    assert r.json()["images"][0]["url"] == url
