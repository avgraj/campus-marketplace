"""Image pipeline: real-image validation, EXIF stripping, caps (plan §7)."""

import io

from PIL import Image

from .conftest import CSRF, dev_login, make_png_bytes


def test_upload_valid_image(client):
    dev_login(client, "alice")
    r = client.post(
        "/uploads/image",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
        headers=CSRF,
    )
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/image/")

    # The processed image is served back from the DB and is a real WebP
    served = client.get(url)
    assert served.status_code == 200
    img = Image.open(io.BytesIO(served.content))
    assert img.format == "WEBP"


def test_non_image_bytes_rejected(client):
    dev_login(client, "alice")
    r = client.post(
        "/uploads/image",
        files={"file": ("evil.png", b"this is not an image at all", "image/png")},
        headers=CSRF,
    )
    assert r.status_code == 400
    assert "not a valid image" in r.json()["detail"]


def test_empty_file_rejected(client):
    dev_login(client, "alice")
    r = client.post("/uploads/image", files={"file": ("e.png", b"", "image/png")}, headers=CSRF)
    assert r.status_code == 400


def test_exif_metadata_is_stripped(client):
    dev_login(client, "alice")
    # Build a JPEG carrying EXIF data (stand-in for phone GPS tags)
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010E] = "shot at my hostel room, gps 12.34,56.78"  # ImageDescription
    img.save(buf, format="JPEG", exif=exif)
    assert Image.open(io.BytesIO(buf.getvalue())).getexif()  # sanity: EXIF present

    r = client.post(
        "/uploads/image",
        files={"file": ("gps.jpg", buf.getvalue(), "image/jpeg")},
        headers=CSRF,
    )
    assert r.status_code == 200, r.text
    served = client.get(r.json()["url"])
    out = Image.open(io.BytesIO(served.content))
    assert dict(out.getexif()) == {}  # stripped by the re-encode


def test_upload_requires_login(client):
    r = client.post(
        "/uploads/image",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
        headers=CSRF,
    )
    assert r.status_code == 401


def test_public_config_and_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    cfg = client.get("/config/public").json()
    assert cfg["community_name"] == "Test Campus"
    assert cfg["dev_mode"] is True
