"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    See backend/.env.example for the full list of required variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Google Cloud Platform
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"

    # Vertex AI / Gemini
    gemini_model: str = "gemini-2.5-flash"

    # Firebase Storage
    firebase_storage_bucket: str = ""

    # CORS — accepts a JSON list or a comma-separated string from the env
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    # File upload limits
    max_file_size_mb: int = 20

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Settings":
        """Raise a combined error at startup if any required field is missing."""
        missing = []
        if not self.gcp_project_id:
            missing.append("GCP_PROJECT_ID")
        if not self.firebase_storage_bucket:
            missing.append("FIREBASE_STORAGE_BUCKET")
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them in your .env file or environment before starting the server."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings instance loaded from environment.

    Raises:
        ValueError: If a required environment variable is missing.
    """
    return Settings()
