"""FastAPI application factory for Vision-First Study Buddy."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# TODO: Import routers once they are implemented
# from app.routers import upload, materials, study_guides, quizzes, health
# from app.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    # TODO: Load settings from config
    # settings = get_settings()

    app = FastAPI(
        title="Vision-First Study Buddy",
        description="Multimodal study tool that processes handwritten notes, photos, PDFs, and epubs into study guides and quizzes.",
        version="1.0.0",
    )

    # TODO: Configure CORS middleware with allowed origins from settings
    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=settings.allowed_origins,
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )

    # TODO: Mount routers
    # app.include_router(health.router, prefix="/api/v1", tags=["health"])
    # app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
    # app.include_router(materials.router, prefix="/api/v1", tags=["materials"])
    # app.include_router(study_guides.router, prefix="/api/v1", tags=["study-guides"])
    # app.include_router(quizzes.router, prefix="/api/v1", tags=["quizzes"])

    return app


# TODO: Initialize the app instance
# app = create_app()
app = FastAPI(title="Vision-First Study Buddy -- Stub")
