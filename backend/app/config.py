"""Application configuration via pydantic-settings."""

from functools import lru_cache

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

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173"]

    # File upload limits
    max_file_size_mb: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings instance loaded from environment.
    """
    # TODO: Add validation to ensure required fields are set
    return Settings()
