"""Shared FastAPI dependency factories."""

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.material_processor import MaterialProcessor
from app.services.storage_client import StorageClient


def get_storage_client(settings: Settings = Depends(get_settings)) -> StorageClient:
    """Return a StorageClient configured for the current bucket."""
    return StorageClient(settings.firebase_storage_bucket)


def get_material_processor(settings: Settings = Depends(get_settings)) -> MaterialProcessor:
    """Return a MaterialProcessor configured with current settings."""
    return MaterialProcessor(settings)
