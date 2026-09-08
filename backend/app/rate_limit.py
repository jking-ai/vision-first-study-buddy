"""Per-IP rate limiting via slowapi.

Defends Vertex AI / Gemini-backed endpoints against cost-runaway abuse.
Cloud Run is configured with `allUsers` invoker, so the public URL has no
auth gate — slowapi imposes a per-IP budget at the FastAPI layer instead.

Limits (per real client IP):

| Endpoint                                  | Per minute | Per day |
|-------------------------------------------|------------|---------|
| POST /api/v1/study-guides/generate        | 5          | 30      |
| POST /api/v1/quizzes/generate             | 5          | 30      |
| POST /api/v1/quizzes/{quiz_id}/submit     | 20         | 200     |
| POST /api/v1/materials/upload             | 10         | 100     |

GET endpoints (health, list, get-by-id) are not limited.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded


def get_client_ip(request: Request) -> str:
    """Resolve the real client IP, honoring X-Forwarded-For from Cloud Run.

    Cloud Run terminates TLS at its load balancer and forwards requests with
    `X-Forwarded-For: <client>, <proxy>, ...`. The leftmost entry is the
    original client. If the header is missing (local dev, internal calls),
    fall back to the direct peer address.

    Args:
        request: The incoming FastAPI/Starlette request.

    Returns:
        The client IP as a string. Returns "unknown" if no IP is resolvable.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP; subsequent entries are proxies.
        first = forwarded.split(",")[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


# Endpoint-specific limit strings. Centralized so AGENTS.md / docs can stay
# in sync, and so tests can import them.
STUDY_GUIDE_GENERATE_LIMITS = "5/minute;30/day"
QUIZ_GENERATE_LIMITS = "5/minute;30/day"
QUIZ_SUBMIT_LIMITS = "20/minute;200/day"
MATERIAL_UPLOAD_LIMITS = "10/minute;100/day"

# Voice Mode session caps (enforced per-device/global/concurrency via VoiceSessionGuard;
# see Settings in app/config.py):
# - VOICE_SESSION_MAX_SECONDS: 180 (3 minutes per session)
# - VOICE_SESSIONS_PER_DEVICE_PER_DAY: 2 (per device per UTC day)
# - VOICE_SESSIONS_PER_DAY_GLOBAL: 20 (global per UTC day)
# - VOICE_MAX_CONCURRENT_SESSIONS: 2
# - VOICE_IDLE_TIMEOUT_SECONDS: 45
# - Inbound audio byte quota: 16000 * 2 * VOICE_SESSION_MAX_SECONDS bytes


# headers_enabled is False on the Limiter itself: when both `SlowAPIMiddleware`
# and `@limiter.limit` decorators are in play, the middleware is the one that
# injects X-RateLimit-* headers onto the final Response. The decorator's own
# header injection requires a `Response` parameter on the path operation
# function, which our handlers don't take (they return Pydantic models),
# so leaving it on raises at runtime.
limiter = Limiter(key_func=get_client_ip, headers_enabled=False)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return a clear JSON 429 when a rate limit is hit.

    The default slowapi handler returns plain text. Frontend / clients here
    expect a structured `{"detail": {"code", "message"}}` envelope, matching
    the rest of the API's error responses.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": {
                "code": "RATE_LIMITED",
                "message": (
                    f"Rate limit exceeded: {exc.detail}. "
                    "Please slow down and try again shortly."
                ),
            }
        },
        headers={"Retry-After": "60"},
    )
