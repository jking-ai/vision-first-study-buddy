"""FastAPI application factory for Vision-First Study Buddy."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.routers import health, materials, quizzes, study_guides, upload, voice

# App loggers emit at INFO so voice tool-call outcomes reach Cloud Run logs.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(logging.INFO)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    # Disable interactive docs unless DOCS_ENABLED=true (default false).
    # Production should never expose /docs, /redoc, or the OpenAPI schema —
    # they advertise the API surface to anyone scraping the public URL.
    docs_kwargs: dict[str, str | None] = (
        {}
        if settings.docs_enabled
        else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    )

    app = FastAPI(
        title="Vision-First Study Buddy",
        description="Multimodal study tool that processes handwritten notes, photos, PDFs, and epubs into study guides and quizzes.",
        version="1.0.0",
        **docs_kwargs,
    )

    # Per-IP rate limiting — defends Gemini-backed endpoints against
    # cost-runaway abuse. See app/rate_limit.py for the limit table.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Device-ID"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
    app.include_router(materials.router, prefix="/api/v1", tags=["materials"])
    app.include_router(study_guides.router, prefix="/api/v1", tags=["study-guides"])
    app.include_router(quizzes.router, prefix="/api/v1", tags=["quizzes"])
    app.include_router(voice.router, prefix="/api/v1", tags=["voice"])

    return app


app = create_app()
