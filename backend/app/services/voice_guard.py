"""Session concurrency and daily rate limit guard for Voice Mode."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

from app.config import Settings, get_settings


class VoiceCapError(Exception):
    """Raised when a voice session limit is reached."""

    def __init__(self, close_code: int, error_code: str, message: str) -> None:
        self.close_code = close_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class VoiceSessionGuard:
    """In-process guard tracking daily sessions and active concurrency.

    Note: Because this operates in-memory, accuracy depends on Cloud Run running
    with --max-instances=1 (or local dev single-instance).
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_date: date = datetime.now(timezone.utc).date()
        self._global_daily_count: int = 0
        self._device_daily_counts: dict[str, int] = {}
        self._active_sessions: int = 0

    def _rollover_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._current_date:
            self._current_date = today
            self._global_daily_count = 0
            self._device_daily_counts.clear()

    async def acquire(self, device_id: str, settings: Settings | None = None) -> None:
        """Attempt to acquire a voice session slot.

        Args:
            device_id: Identifier of the requesting device.
            settings: Optional settings override.

        Raises:
            VoiceCapError: If voice is disabled or any cap is exceeded.
        """
        if settings is None:
            settings = get_settings()

        if not settings.voice_enabled:
            raise VoiceCapError(4503, "VOICE_DISABLED", "Voice mode is turned off right now.")

        async with self._lock:
            self._rollover_if_new_day()

            if self._active_sessions >= settings.voice_max_concurrent_sessions:
                raise VoiceCapError(
                    4429,
                    "CONCURRENT_LIMIT",
                    "The coach is busy with other students right now. Try again in a few minutes.",
                )

            if self._global_daily_count >= settings.voice_sessions_per_day_global:
                raise VoiceCapError(
                    4429,
                    "GLOBAL_DAILY_LIMIT",
                    "The voice coach is fully booked today. Try again tomorrow.",
                )

            device_count = self._device_daily_counts.get(device_id, 0)
            if device_count >= settings.voice_sessions_per_device_per_day:
                raise VoiceCapError(
                    4429,
                    "DEVICE_DAILY_LIMIT",
                    "You've used today's voice sessions on this device. Come back tomorrow.",
                )

            self._active_sessions += 1
            self._global_daily_count += 1
            self._device_daily_counts[device_id] = device_count + 1

    async def release(self, device_id: str, refund: bool = False) -> None:
        """Release an active session slot upon session end.

        If refund is True, decrements daily session counts so failed/aborted
        sessions don't penalize the user.
        """
        async with self._lock:
            if self._active_sessions > 0:
                self._active_sessions -= 1
            if refund:
                if self._global_daily_count > 0:
                    self._global_daily_count -= 1
                if device_id in self._device_daily_counts and self._device_daily_counts[device_id] > 0:
                    self._device_daily_counts[device_id] -= 1

    async def get_remaining_today(self, device_id: str, settings: Settings | None = None) -> int:
        """Return the number of voice sessions remaining for the device today.

        Args:
            device_id: Identifier of the requesting device.
            settings: Optional settings override.

        Returns:
            Remaining session count for the current UTC day, floored at 0.
        """
        if settings is None:
            settings = get_settings()

        if not settings.voice_enabled:
            return 0

        async with self._lock:
            self._rollover_if_new_day()
            used = self._device_daily_counts.get(device_id, 0)
            return max(0, settings.voice_sessions_per_device_per_day - used)

    def reset(self) -> None:
        """Reset all counters. Used in test fixture cleanup."""
        self._current_date = datetime.now(timezone.utc).date()
        self._global_daily_count = 0
        self._device_daily_counts.clear()
        self._active_sessions = 0


# Shared singleton instance
guard = VoiceSessionGuard()
