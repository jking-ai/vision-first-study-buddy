"""Health check router."""

from fastapi import APIRouter

# TODO: Import config and response models once implemented
# from app.config import get_settings
# from app.models.responses import HealthResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return service health status and metadata.

    Used by Cloud Run health checks and frontend connectivity verification.

    Returns:
        HealthResponse with service status, version, model, and storage bucket.
    """
    # TODO: Implement health check with real config values
    # settings = get_settings()
    # return HealthResponse(
    #     status="healthy",
    #     service="vision-first-study-buddy",
    #     version="1.0.0",
    #     model=settings.gemini_model,
    #     storage_bucket=settings.firebase_storage_bucket,
    # )
    return {"status": "healthy", "service": "vision-first-study-buddy", "version": "0.0.1-stub"}
