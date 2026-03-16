"""Shared FastAPI dependency factories."""

from fastapi import Depends

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


def get_gemini_client(settings: Settings = Depends(get_settings)) -> GeminiClient:
    """Return a GeminiClient configured for the current GCP project."""
    return GeminiClient(
        project_id=settings.gcp_project_id,
        region=settings.gcp_region,
        model_name=settings.gemini_model,
    )


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
