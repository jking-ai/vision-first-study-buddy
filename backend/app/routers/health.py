"""Health check router."""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return service health status and metadata.

    Used by Cloud Run health checks and frontend connectivity verification.

    Returns:
        HealthResponse with service status, version, model, and storage bucket.
    """
    return HealthResponse(
        status="healthy",
        service="vision-first-study-buddy",
        version="1.0.0",
        model=settings.gemini_model,
        storage_bucket=settings.firebase_storage_bucket,
    )
