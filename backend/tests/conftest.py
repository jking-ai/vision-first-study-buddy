"""Pytest configuration and shared fixtures for the backend test suite."""

import os

import pytest

# Set required environment variables before any app module is imported.
# These must be in place before `app.main` loads `create_app()` at module level.
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("FIREBASE_STORAGE_BUCKET", "test-project.appspot.com")
# Tests run with a non-empty CORS origin list so cors-related assertions
# still fire — the production default in code is empty (non-permissive).
# Pydantic-settings parses list[str] env vars as JSON when present, so we
# encode the list rather than rely on the comma-separated fallback.
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:5173"]')


# Several test files have their own autouse fixtures that call
# `app.dependency_overrides.clear()`. To install a global default override
# for `get_device_id` that survives those clears, we replace the
# overrides dict with a subclass that preserves a registered "sticky" key.
class _StickyOverrides(dict):
    """dict that protects entries listed in `_sticky_keys` from being cleared.

    When test code calls `app.dependency_overrides.clear()`, normal entries
    are removed but anything in `_sticky_keys` is preserved. This lets the
    conftest install a default `get_device_id` override that survives
    per-test cleanup.
    """

    _sticky_keys: set = set()

    def clear(self) -> None:  # type: ignore[override]
        sticky = {k: self[k] for k in self._sticky_keys if k in self}
        super().clear()
        super().update(sticky)


def _install_sticky_overrides() -> None:
    from app.dependencies import get_device_id
    from app.main import app

    if isinstance(app.dependency_overrides, _StickyOverrides):
        return
    sticky = _StickyOverrides(app.dependency_overrides)
    sticky[get_device_id] = lambda: "test-device"
    sticky._sticky_keys = {get_device_id}
    app.dependency_overrides = sticky


_install_sticky_overrides()


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_caches, DI overrides, and per-IP rate-limit counters between tests."""
    from app.config import get_settings
    from app.dependencies import _cached_gemini_client
    from app.main import app
    from app.rate_limit import limiter

    get_settings.cache_clear()
    _cached_gemini_client.cache_clear()
    app.dependency_overrides.clear()
    # Reset slowapi's in-memory storage so a previous test's hits don't bleed
    # into the next one.
    limiter.reset()
    yield
    get_settings.cache_clear()
    _cached_gemini_client.cache_clear()
    app.dependency_overrides.clear()
    limiter.reset()
