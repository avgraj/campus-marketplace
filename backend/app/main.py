"""FastAPI application entrypoint.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs (free auto-generated Swagger UI, plan §2)
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import settings
from .database import Base, SessionLocal, engine
from .rate_limit import limiter
from .routers import admin, auth, categories, listings, uploads
from .schemas import PublicConfigOut
from .seed import seed_categories


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_categories(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Campus Marketplace API", version="1.0.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS locked to the real frontend origin — never "*" for cookie routes (plan §11).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth.router)
    app.include_router(categories.router)
    app.include_router(listings.router)
    app.include_router(uploads.router)
    app.include_router(admin.router)

    # Working-model image storage: processed files on disk, served back here.
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/config/public", response_model=PublicConfigOut)
    def public_config() -> PublicConfigOut:
        """Non-secret config the SPA needs to render (branding, login button)."""
        return PublicConfigOut(
            community_name=settings.community_name,
            telegram_bot_username=settings.telegram_bot_username,
            dev_mode=settings.dev_mode,
        )

    return app


app = create_app()
