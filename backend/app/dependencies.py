"""Shared FastAPI dependency factories."""

import functools

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.services.gemini_client import GeminiClient
from app.services.material_processor import MaterialProcessor
from app.services.quiz_generator import QuizGenerator
from app.services.storage_client import StorageClient
from app.services.study_guide_generator import StudyGuideGenerator


def get_storage_client(settings: Settings = Depends(get_settings)) -> StorageClient:
    """Return a StorageClient configured for the current bucket."""
    return StorageClient(settings.firebase_storage_bucket)


def get_material_processor(settings: Settings = Depends(get_settings)) -> MaterialProcessor:
    """Return a MaterialProcessor configured with current settings."""
    return MaterialProcessor(settings)


@functools.lru_cache(maxsize=4)
def _cached_gemini_client(project_id: str, region: str, model_name: str) -> GeminiClient:
    """Create a GeminiClient and cache it by (project_id, region, model_name).

    vertexai.init() is only called once per unique configuration, not per request.
    Cache size of 4 accommodates test environments that use different settings.
    """
    return GeminiClient(project_id, region, model_name)


def get_gemini_client(settings: Settings = Depends(get_settings)) -> GeminiClient:
    """Return a cached GeminiClient configured for the current project and model."""
    return _cached_gemini_client(settings.gcp_project_id, settings.gcp_region, settings.gemini_model)


def get_study_guide_generator(
    gemini_client: GeminiClient = Depends(get_gemini_client),
    storage_client: StorageClient = Depends(get_storage_client),
    material_processor: MaterialProcessor = Depends(get_material_processor),
) -> StudyGuideGenerator:
    """Return a StudyGuideGenerator with all dependencies injected."""
    return StudyGuideGenerator(gemini_client, storage_client, material_processor)


def get_quiz_generator(
    gemini_client: GeminiClient = Depends(get_gemini_client),
    storage_client: StorageClient = Depends(get_storage_client),
    material_processor: MaterialProcessor = Depends(get_material_processor),
) -> QuizGenerator:
    """Return a QuizGenerator with all dependencies wired."""
    return QuizGenerator(gemini_client, storage_client, material_processor)


async def get_device_id(x_device_id: str = Header(...)) -> str:
    """Extract and validate the X-Device-ID header.

    Each device/browser generates a UUID stored in localStorage and sends it
    with every request. This allows per-device material isolation without auth.

    Args:
        x_device_id: The device identifier from the X-Device-ID header.

    Returns:
        The validated device ID string.

    Raises:
        HTTPException 400: If the header is missing, empty, or too long.
    """
    if not x_device_id or len(x_device_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid X-Device-ID header")
    return x_device_id
