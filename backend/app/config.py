"""Application configuration, loaded from environment variables.

Resolution order for a .env file: ./.env (backend dir) first, then ../.env
(repo root, as committed .env.example suggests). Real environment variables
always win over file values.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_env_candidates = [Path(".env"), Path("../.env")]
_env_file = next((str(p) for p in _env_candidates if p.exists()), ".env")

# Clearly prohibited content, checked at listing creation (plan §12).
# Keep as data so it is easy to extend.
BLOCKED_KEYWORDS = [
    "weapon",
    "firearm",
    "gun",
    "ammunition",
    "drugs",
    "cannabis",
    "weed",
    "narcotic",
    "counterfeit",
    "fake id",
    "alcohol",
    "cigarette",
    "vape",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, env_file_encoding="utf-8", extra="ignore")

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    community_group_chat_id: str = ""

    # Database — SQLite by default so the project runs with zero setup;
    # set DATABASE_URL to Postgres in production.
    database_url: str = "sqlite:///./campus_marketplace.db"

    # Sessions / cookies
    session_secret: str = "change-me-to-a-long-random-string"
    session_ttl_days: int = 30
    # True in production (HTTPS). When True the cookie is SameSite=None;Secure
    # so a cross-site frontend (Vercel → Render) can send it.
    cookie_secure: bool = False

    # Image storage — working model writes to this local dir, served at /uploads.
    upload_dir: str = "uploads"

    # Frontend origin for CORS.
    frontend_origin: str = "http://localhost:5173"

    # Dev mode enables a password-less dev login endpoint. NEVER true in prod.
    dev_mode: bool = False

    # Branding — community name is config, not hardcoded (plan §14).
    community_name: str = "My Campus"

    # Rate limiting (slowapi). Disabled in tests.
    rate_limit_enabled: bool = True

    # Listing rules (plan §6)
    listing_ttl_days: int = 14
    max_active_listings_per_user: int = 10
    max_listings_per_day: int = 5
    max_images_per_listing: int = 5
    max_upload_bytes: int = 5 * 1024 * 1024  # 5MB raw upload cap
    max_image_dimension: int = 1600
    target_image_bytes: int = 300 * 1024  # ~300KB after processing


settings = Settings()
