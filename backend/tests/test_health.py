"""Tests for the health endpoint and application startup."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """Return a Settings instance with required fields and optional overrides."""
    defaults = {
        "gcp_project_id": "test-project",
        "firebase_storage_bucket": "test-project.appspot.com",
        "gemini_model": "gemini-1.5-flash",
        "allowed_origins": ["http://localhost:5173"],
    }
    defaults.update(overrides)
    return Settings.model_construct(**defaults)


def _get_test_client() -> TestClient:
    """Build a TestClient with settings dependency overridden."""
    # Import here so that the module-level `app = create_app()` does not run
    # before we patch get_settings.
    from app.main import app

    test_settings = _make_settings()
    app.dependency_overrides[get_settings] = lambda: test_settings
    client = TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()
    return client


# ---------------------------------------------------------------------------
# Config validation tests
# ---------------------------------------------------------------------------

class TestSettingsValidation:
    def test_raises_when_gcp_project_id_missing(self):
        with pytest.raises(Exception, match="GCP_PROJECT_ID"):
            Settings(
                gcp_project_id="",
                firebase_storage_bucket="bucket.appspot.com",
            )

    def test_raises_when_firebase_storage_bucket_missing(self):
        with pytest.raises(Exception, match="FIREBASE_STORAGE_BUCKET"):
            Settings(
                gcp_project_id="my-project",
                firebase_storage_bucket="",
            )

    def test_allowed_origins_comma_separated_string(self):
        s = Settings.model_validate(
            {
                "gcp_project_id": "p",
                "firebase_storage_bucket": "b.appspot.com",
                "allowed_origins": "http://localhost:5173,https://example.com",
            }
        )
        assert s.allowed_origins == ["http://localhost:5173", "https://example.com"]

    def test_allowed_origins_list(self):
        s = Settings.model_validate(
            {
                "gcp_project_id": "p",
                "firebase_storage_bucket": "b.appspot.com",
                "allowed_origins": ["http://localhost:5173"],
            }
        )
        assert s.allowed_origins == ["http://localhost:5173"]

    def test_defaults_are_sensible(self):
        s = Settings.model_validate(
            {
                "gcp_project_id": "my-project",
                "firebase_storage_bucket": "my-project.appspot.com",
            }
        )
        assert s.gemini_model == "gemini-1.5-flash"
        assert s.gcp_region == "us-central1"
        assert s.max_file_size_mb == 20


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def _client_with_settings(self, **overrides) -> TestClient:
        from app.main import app

        test_settings = _make_settings(**overrides)
        app.dependency_overrides[get_settings] = lambda: test_settings
        client = TestClient(app)
        # Override is intentionally left active for the duration of this test;
        # conftest.clear_settings_cache clears it between tests via autouse.
        return client

    def test_health_returns_200(self):
        client = self._client_with_settings()
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_shape(self):
        client = self._client_with_settings()
        data = client.get("/api/v1/health").json()
        assert data["status"] == "healthy"
        assert data["service"] == "vision-first-study-buddy"
        assert data["version"] == "1.0.0"
        assert "model" in data
        assert "storage_bucket" in data

    def test_health_returns_configured_model(self):
        client = self._client_with_settings(gemini_model="gemini-1.5-pro")
        data = client.get("/api/v1/health").json()
        assert data["model"] == "gemini-1.5-pro"

    def test_health_returns_configured_bucket(self):
        client = self._client_with_settings(
            firebase_storage_bucket="my-bucket.appspot.com"
        )
        data = client.get("/api/v1/health").json()
        assert data["storage_bucket"] == "my-bucket.appspot.com"
