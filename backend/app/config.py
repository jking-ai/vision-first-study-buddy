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
    gemini_location: str = "global"
    gemini_api_endpoint: str = "aiplatform.googleapis.com"
    gemini_model: str = "gemini-3.1-pro-preview"

    # Firebase Storage
    firebase_storage_bucket: str = ""

    # CORS — accepts a JSON list or a comma-separated string from the env.
    # Default is empty (non-permissive): production must set ALLOWED_ORIGINS
    # explicitly. Local dev should set ALLOWED_ORIGINS in .env to localhost URLs.
    allowed_origins: list[str] = []

    # File upload limits
    max_file_size_mb: int = 20

    # Interactive docs (Swagger UI / ReDoc / OpenAPI schema).
    # Defaults to False so production never exposes the API surface map.
    # Set DOCS_ENABLED=true in local dev if you want /docs back.
    docs_enabled: bool = False

    # Voice Coach settings
    voice_enabled: bool = False
    gemini_live_api_key: str = ""
    gemini_live_model: str = "gemini-3.1-flash-live-preview"
    voice_coach_voice: str = "Kore"
    voice_allowed_voices: list[str] = [
        "Kore",
        "Puck",
        "Charon",
        "Aoede",
        "Fenrir",
        "Leda",
        "Orus",
        "Zephyr",
    ]
    voice_session_max_seconds: int = 180
    voice_sessions_per_device_per_day: int = 5
    voice_sessions_per_day_global: int = 30
    voice_max_concurrent_sessions: int = 2
    voice_idle_timeout_seconds: int = 45
    voice_start_timeout_seconds: float = 5.0
    voice_max_guide_bytes: int = 32768
    voice_audio_in_price_per_m: float = 3.0
    voice_audio_out_price_per_m: float = 12.0
    voice_quiz_questions: int = 5
    # Silence the client inserts in playback between the tutor's feedback on an
    # answer and the next question (sent as a "pause" frame after each record).
    voice_next_question_pause_seconds: float = 2.5
    # After the time limit, input is locked; the coach may finish its current
    # turn for up to this many seconds before the session ends.
    voice_end_grace_seconds: int = 30

    @property
    def voice_audio_quota_bytes(self) -> int:
        """Derived inbound audio byte quota per session."""
        return 16000 * 2 * self.voice_session_max_seconds

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    @field_validator("voice_allowed_voices", mode="before")
    @classmethod
    def parse_voice_allowed_voices(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [voice.strip() for voice in v.split(",") if voice.strip()]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_required_fields(self) -> "Settings":
        """Raise a combined error at startup if any required field is missing."""
        missing = []
        if not self.gcp_project_id:
            missing.append("GCP_PROJECT_ID")
        if not self.firebase_storage_bucket:
            missing.append("FIREBASE_STORAGE_BUCKET")
        if self.voice_enabled and not self.gemini_live_api_key:
            missing.append("GEMINI_LIVE_API_KEY")
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
