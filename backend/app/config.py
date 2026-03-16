"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    See backend/.env.example for the full list of required variables.
    """

    # Google Cloud Platform
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"

    # Vertex AI / Gemini
    gemini_model: str = "gemini-1.5-flash"

    # Firebase Storage
    firebase_storage_bucket: str = ""

    # CORS — accepts a JSON list or a comma-separated string from the env
    allowed_origins: list[str] = ["http://localhost:5173"]

    # File upload limits
    max_file_size_mb: int = 20

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("gcp_project_id")
    @classmethod
    def require_gcp_project_id(cls, v: str) -> str:
        if not v:
            raise ValueError("GCP_PROJECT_ID is required but was not set")
        return v

    @field_validator("firebase_storage_bucket")
    @classmethod
    def require_firebase_storage_bucket(cls, v: str) -> str:
        if not v:
            raise ValueError("FIREBASE_STORAGE_BUCKET is required but was not set")
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings instance loaded from environment.

    Raises:
        ValueError: If a required environment variable is missing.
    """
    return Settings()
