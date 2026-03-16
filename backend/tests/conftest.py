"""Pytest configuration and shared fixtures for the backend test suite."""

import os

import pytest

# Set required environment variables before any app module is imported.
# These must be in place before `app.main` loads `create_app()` at module level.
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_STORAGE_BUCKET", "test-project.appspot.com")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache on get_settings and any DI overrides between tests."""
    from app.config import get_settings
    from app.main import app

    get_settings.cache_clear()
    app.dependency_overrides.clear()
    yield
    get_settings.cache_clear()
    app.dependency_overrides.clear()
