"""Pydantic request/response models — strict lengths and numeric bounds (plan §11)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Condition = Literal["new", "like_new", "used", "for_parts"]

PRICE_CAP = 1_000_000  # sane upper cap to catch typos (plan §6)


# ── Auth ──────────────────────────────────────────────────────────────────────


class CodeRequestIn(BaseModel):
    """Step 1 of OTP login: the Telegram @username to send a code to."""

    username: str = Field(min_length=3, max_length=40)


class CodeVerifyIn(BaseModel):
    """Step 2: username + the 6-digit code the bot DMed."""

    username: str = Field(min_length=3, max_length=40)
    code: str = Field(pattern=r"^\d{6}$")


class DevLoginIn(BaseModel):
    """Only available when DEV_MODE=true — bypasses Telegram for local dev/demo."""

    username: str = Field(default="devuser", min_length=3, max_length=32)
    first_name: str = Field(default="Dev User", max_length=64)
    as_admin: bool = False


class UserOut(BaseModel):
    id: int
    telegram_username: str | None
    first_name: str
    last_name: str | None
    photo_url: str | None
    is_verified_member: bool
    is_admin: bool

    model_config = {"from_attributes": True}


# ── Categories ────────────────────────────────────────────────────────────────


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


# ── Listings ──────────────────────────────────────────────────────────────────


class ListingCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=20, max_length=1000)
    price: float = Field(gt=0, le=PRICE_CAP)
    category_id: int
    condition: Condition
    is_negotiable: bool = False
    image_urls: list[str] = Field(min_length=1, max_length=5)

    @field_validator("image_urls")
    @classmethod
    def urls_must_be_ours(cls, urls: list[str]) -> list[str]:
        for u in urls:
            if not (u.startswith("/uploads/") or u.startswith("/image/")):
                raise ValueError("image urls must come from POST /uploads/image")
        return urls


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=120)
    description: str | None = Field(default=None, min_length=20, max_length=1000)
    price: float | None = Field(default=None, gt=0, le=PRICE_CAP)
    category_id: int | None = None
    condition: Condition | None = None
    is_negotiable: bool | None = None
    image_urls: list[str] | None = Field(default=None, min_length=1, max_length=5)

    @field_validator("image_urls")
    @classmethod
    def urls_must_be_ours(cls, urls: list[str] | None) -> list[str] | None:
        if urls:
            for u in urls:
                if not (u.startswith("/uploads/") or u.startswith("/image/")):
                    raise ValueError("image urls must come from POST /uploads/image")
        return urls


class ImageOut(BaseModel):
    id: int
    url: str
    position: int

    model_config = {"from_attributes": True}


class SellerOut(BaseModel):
    first_name: str
    # Username only leaves the server on the detail endpoint for logged-in
    # members (the contact flow), never in public browse payloads.
    telegram_username: str | None = None

    model_config = {"from_attributes": True}


class ListingCardOut(BaseModel):
    id: int
    title: str
    price: float
    is_negotiable: bool
    condition: str
    status: str
    created_at: datetime
    category: CategoryOut
    images: list[ImageOut]

    model_config = {"from_attributes": True}


class ListingDetailOut(ListingCardOut):
    description: str
    expires_at: datetime
    seller: SellerOut
    is_mine: bool = False


class ListingPageOut(BaseModel):
    items: list[ListingCardOut]
    total: int
    page: int
    page_size: int


# ── Reports / admin ───────────────────────────────────────────────────────────


class ReportCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class ReportOut(BaseModel):
    id: int
    reason: str
    status: str
    created_at: datetime
    listing: ListingCardOut
    reporter: UserOut

    model_config = {"from_attributes": True}


# ── Misc ──────────────────────────────────────────────────────────────────────


class UploadOut(BaseModel):
    url: str


class PublicConfigOut(BaseModel):
    community_name: str
    telegram_bot_username: str
    dev_mode: bool
    # Exposed so we can debug CORS without shell access — it's the site's own
    # public URL, visible in CORS response headers anyway.
    frontend_origin: str
