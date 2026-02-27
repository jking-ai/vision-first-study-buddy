# Phase 1: Backend Project Setup & Health Endpoint — Design Spec

**Date:** 2026-03-15
**Issue:** jking-ai/vision-first-study-buddy#1
**Branch:** feature/dashboard-97471d63

## Overview

Wire up the FastAPI application factory with configuration management, CORS middleware, all 5 routers mounted, and a working health check endpoint. This is the foundation all other backend work builds on.

## Scope

Files to create:
- `backend/app/routers/__init__.py` — empty package marker
- `backend/app/models/__init__.py` — empty package marker
- `docs/superpowers/specs/2026-03-15-phase1-backend-setup-design.md` — this file

Files to modify:
- `backend/app/config.py` — migrate `class Config` to `SettingsConfigDict`, add `@field_validator` for comma-separated `allowed_origins`, add `@model_validator(mode="after")` to validate required fields together
- `backend/app/main.py` — uncomment and complete `create_app()` with CORS + all 5 routers; replace stub app instance *(done in PR #16)*
- `backend/app/routers/health.py` — inject `Settings` via `Depends(get_settings)`, return real config values via `HealthResponse` *(done in PR #16)*
- `backend/Dockerfile` — install `curl` cleanly, add `HEALTHCHECK` using curl, add non-root user
- `backend/tests/test_health.py` — refactor to pytest fixtures, add CORS header test
- `AGENTS.md` — update status + document required env vars

## Design Decisions

### Config Validation (`config.py`)

**Migrate to `SettingsConfigDict`:** Replace the pydantic v1-style `class Config` inner class (or plain dict) with `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")` — the canonical pydantic-settings v2 form.

**Comma-separated `allowed_origins`:** pydantic-settings v2 does not auto-split comma-separated env var strings into lists — it expects JSON. Add `@field_validator("allowed_origins", mode="before")` that splits on commas when the input is a plain string, preserving compatibility with the `.env.example` format (`ALLOWED_ORIGINS=http://localhost:5173`).

**Required field validation with `@model_validator`:** Both `gcp_project_id` and `firebase_storage_bucket` have defaults of `""` so pydantic can construct the Settings object. Use `@model_validator(mode="after")` to check both fields together and raise a combined, descriptive `ValueError` at startup. This is more idiomatic than two separate `@field_validator`s — it produces a single clear error message when multiple required fields are missing, and it's the correct pattern for cross-field validation in pydantic v2.

### App Factory (`main.py`) *(implemented in PR #16)*

Remove the stub `app = FastAPI(title="Vision-First Study Buddy -- Stub")`. Uncomment all TODO blocks: import `get_settings` and all 5 routers (`health`, `upload`, `materials`, `study_guides`, `quizzes`), call `create_app()` to build the real app instance. CORS uses `settings.allowed_origins`.

### Health Router (`routers/health.py`) *(implemented in PR #16)*

Use `Depends(get_settings)` for dependency injection. Return `HealthResponse` with `status="healthy"`, `service="vision-first-study-buddy"`, `version="1.0.0"`, `model=settings.gemini_model`, `storage_bucket=settings.firebase_storage_bucket`.

### Dockerfile

**Install curl cleanly** (needed for HEALTHCHECK):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
```

**Non-root user:** Use `useradd` (not `adduser`) to avoid interactive GECOS prompts on Debian-based images:
```dockerfile
RUN useradd --no-create-home --shell /bin/false nonroot
USER nonroot
```

**HEALTHCHECK:** Use `curl -f` for the probe — more reliable than Python's `urllib.request.urlopen` for a Docker health check since it properly handles non-2xx status codes with `-f`. Note that Cloud Run does not use Docker `HEALTHCHECK` — it uses its own HTTP probe; this instruction is only effective locally.
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1
```

### Tests

Refactor from class-based tests to function-based tests with pytest fixtures:
- `make_settings(**kwargs)` helper creates `Settings` via `model_validate` (bypasses env file)
- `test_settings` fixture provides a standard Settings instance for endpoint tests
- `client` fixture builds `TestClient` with `dependency_overrides` for `get_settings`
- Add `test_health_cors_headers` to verify CORS middleware is wired correctly

## Success Criteria

1. `uvicorn app.main:app --reload` starts without errors when `.env` has required variables set
2. `GET /api/v1/health` returns `{"status":"healthy","service":"vision-first-study-buddy","version":"1.0.0","model":"gemini-2.5-flash","storage_bucket":"..."}`
3. Starting without `GCP_PROJECT_ID` or `FIREBASE_STORAGE_BUCKET` raises a clear `ValueError` listing all missing fields
4. `pytest` passes all 11 tests covering config validation, health endpoint shape, and CORS headers
