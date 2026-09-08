"""Voice Coach WebSocket relay and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.dependencies import get_device_id, get_live_client
from app.services.live_client import LiveClient
from app.services.voice_guard import guard
from app.services.voice_session import VoiceSessionCoordinator

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceStatusResponse(BaseModel):
    """Status and cap availability for Voice Mode."""

    enabled: bool
    max_duration_s: int
    sessions_per_device_per_day: int
    remaining_today: int
    model: str


@router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status(
    device_id: str = Depends(get_device_id),
    settings: Settings = Depends(get_settings),
) -> VoiceStatusResponse:
    """Return voice mode availability, caps, and remaining sessions for the device."""
    remaining = await guard.get_remaining_today(device_id, settings)
    return VoiceStatusResponse(
        enabled=settings.voice_enabled,
        max_duration_s=settings.voice_session_max_seconds,
        sessions_per_device_per_day=settings.voice_sessions_per_device_per_day,
        remaining_today=remaining,
        model=settings.gemini_live_model,
    )


@router.websocket("/session")
async def voice_session_endpoint(
    websocket: WebSocket,
    live_client: LiveClient = Depends(get_live_client),
    settings: Settings = Depends(get_settings),
) -> None:
    """WebSocket endpoint for Voice Coach live bidirectional audio session."""
    coordinator = VoiceSessionCoordinator(
        websocket=websocket,
        live_client=live_client,
        guard=guard,
        settings=settings,
    )
    await coordinator.run()
