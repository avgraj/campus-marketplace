"""Admin moderation: report queue, removal, ban with session invalidation."""

from fastapi.testclient import TestClient

from app.main import app

from .conftest import CSRF, create_listing, dev_login


def _fresh_client():
    return TestClient(app)


def test_admin_queue_remove_and_ban(client):
    # Seller + a reported listing
    dev_login(client, "bob")
    listing_id = create_listing(client, title="Shady Item For Admin").json()["id"]
    client.post(f"/listings/{listing_id}/report", json={"reason": "suspicious"}, headers=CSRF)

    # Non-admin is refused
    assert client.get("/admin/reports", headers=CSRF).status_code == 403

    with _fresh_client() as admin:
        dev_login(admin, "mod-user", as_admin=True)
        with admin:
            queue = admin.get("/admin/reports", headers=CSRF)
            assert queue.status_code == 200, queue.text
            items = queue.json()
            assert len(items) == 1
            assert items[0]["listing"]["id"] == listing_id
            assert items[0]["reason"] == "suspicious"

            # Remove the listing → queue clears, listing 404s publicly
            assert admin.post(f"/admin/listings/{listing_id}/remove", headers=CSRF).status_code == 204
            assert admin.get("/admin/reports", headers=CSRF).json() == []

            # Ban the seller → their session dies immediately (plan §12)
            bob_id = client.get("/auth/me").json()["id"]
            assert admin.post(f"/admin/users/{bob_id}/ban", headers=CSRF).status_code == 204

    assert client.get(f"/listings/{listing_id}").status_code == 404
    assert client.get("/auth/me").status_code == 401  # banned + session revoked


def test_admin_cannot_ban_self(client):
    dev_login(client, "solo-admin", as_admin=True)
    my_id = client.get("/auth/me").json()["id"]
    r = client.post(f"/admin/users/{my_id}/ban", headers=CSRF)
    assert r.status_code == 400


def test_dismiss_report(client):
    dev_login(client, "dave")
    listing_id = create_listing(client, title="Dismissable Report Item").json()["id"]
    client.post(f"/listings/{listing_id}/report", json={"reason": "wrong category"}, headers=CSRF)

    with _fresh_client() as admin:
        dev_login(admin, "mod-two", as_admin=True)
        with admin:
            report_id = admin.get("/admin/reports", headers=CSRF).json()[0]["id"]
            assert admin.post(f"/admin/reports/{report_id}/dismiss", headers=CSRF).status_code == 204
            assert admin.get("/admin/reports", headers=CSRF).json() == []
    # Listing survives a dismissed report
    assert client.get(f"/listings/{listing_id}").status_code == 200
