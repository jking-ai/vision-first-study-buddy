"""Tests for the per-IP rate limiter that defends Gemini-backed endpoints.

The Limiter is configured per-endpoint in `app/rate_limit.py`. These tests
verify the happy path: under the limit returns success; the first request
beyond the limit returns HTTP 429 with the structured RATE_LIMITED envelope.

`tests/conftest.py` calls `limiter.reset()` between tests so per-IP
counters don't bleed across runs.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_quiz_generator
from app.main import app
from app.rate_limit import limiter
from tests.test_quizzes import make_quiz_generator_mock


GENERATE_URL = "/api/v1/quizzes/generate"


@pytest.mark.asyncio
async def test_quiz_generate_returns_429_after_per_minute_limit():
    """The quizzes/generate endpoint allows 5/minute. The 6th call must 429."""
    # Sanity: starting fresh.
    limiter.reset()
    mock = make_quiz_generator_mock()
    app.dependency_overrides[get_quiz_generator] = lambda: mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 5 calls allowed within a minute.
        for i in range(5):
            r = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
            assert r.status_code == 201, f"call {i + 1} unexpectedly failed: {r.status_code} {r.text}"

        # 6th call within the same minute must hit the limit.
        r = await client.post(GENERATE_URL, json={"material_ids": ["mat_001"]})
        assert r.status_code == 429
        body = r.json()
        assert body["detail"]["code"] == "RATE_LIMITED"
        assert "rate limit" in body["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_health_endpoint_is_not_rate_limited():
    """Health check has no decorator and must remain unbounded."""
    limiter.reset()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(50):
            r = await client.get("/api/v1/health")
            assert r.status_code == 200
