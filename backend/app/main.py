"""FastAPI application factory for Vision-First Study Buddy."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, materials, quizzes, study_guides, upload
from app.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Vision-First Study Buddy",
        description="Multimodal study tool that processes handwritten notes, photos, PDFs, and epubs into study guides and quizzes.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Device-ID"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
    app.include_router(materials.router, prefix="/api/v1", tags=["materials"])
    app.include_router(study_guides.router, prefix="/api/v1", tags=["study-guides"])
    app.include_router(quizzes.router, prefix="/api/v1", tags=["quizzes"])

    return app


app = create_app()
