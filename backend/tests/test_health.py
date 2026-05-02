"""Tests for the health endpoint and application startup."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_settings(**kwargs) -> Settings:
    """Create a Settings instance with required fields set, overriding with kwargs."""
    defaults = {
        "gcp_project_id": "test-project",
        "firebase_storage_bucket": "test-project.appspot.com",
    }
    defaults.update(kwargs)
    return Settings.model_validate(defaults)


@pytest.fixture
def test_settings() -> Settings:
    return make_settings(
        gemini_model="gemini-3.1-pro-preview",
        firebase_storage_bucket="my-project.appspot.com",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


# ---------------------------------------------------------------------------
# Config validation tests
# ---------------------------------------------------------------------------


def test_settings_valid():
    s = make_settings()
    assert s.gcp_project_id == "test-project"
    assert s.firebase_storage_bucket == "test-project.appspot.com"


def test_settings_missing_gcp_project_id():
    with pytest.raises(ValidationError) as exc_info:
        make_settings(gcp_project_id="")
    assert "GCP_PROJECT_ID" in str(exc_info.value)


def test_settings_missing_firebase_storage_bucket():
    with pytest.raises(ValidationError) as exc_info:
        make_settings(firebase_storage_bucket="")
    assert "FIREBASE_STORAGE_BUCKET" in str(exc_info.value)


def test_settings_missing_both_required_fields():
    with pytest.raises(ValidationError) as exc_info:
        make_settings(gcp_project_id="", firebase_storage_bucket="")
    error_str = str(exc_info.value)
    assert "GCP_PROJECT_ID" in error_str
    assert "FIREBASE_STORAGE_BUCKET" in error_str


def test_settings_allowed_origins_comma_separated():
    s = make_settings(allowed_origins="http://localhost:5173,https://app.example.com")
    assert s.allowed_origins == ["http://localhost:5173", "https://app.example.com"]


def test_settings_allowed_origins_single():
    s = make_settings(allowed_origins="http://localhost:5173")
    assert s.allowed_origins == ["http://localhost:5173"]


def test_settings_allowed_origins_list():
    s = make_settings(allowed_origins=["http://localhost:5173", "https://app.example.com"])
    assert s.allowed_origins == ["http://localhost:5173", "https://app.example.com"]


def test_settings_defaults_are_sensible():
    # gemini_model can be overridden by a developer's local .env, so we only
    # assert that the field has a sensible non-empty default.
    s = make_settings()
    assert s.gemini_model
    assert s.gcp_region == "us-central1"
    assert s.max_file_size_mb == 20


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------


def test_health_returns_200(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_shape(client: TestClient, test_settings: Settings):
    data = client.get("/api/v1/health").json()
    assert data["status"] == "healthy"
    assert data["service"] == "vision-first-study-buddy"
    assert data["version"] == "1.0.0"
    assert data["model"] == test_settings.gemini_model
    assert data["storage_bucket"] == test_settings.firebase_storage_bucket


def test_health_cors_headers(client: TestClient):
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
