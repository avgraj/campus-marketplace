"""Per-route rate limiting via slowapi (plan §11) — tighter on writes than reads."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)

# Conventional limits used across the routers.
AUTH_LIMIT = "10/minute"
WRITE_LIMIT = "10/minute"
UPLOAD_LIMIT = "20/minute"
READ_LIMIT = "120/minute"
