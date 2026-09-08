"""Live API client abstraction and Google GenAI implementation."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from google import genai
from google.genai import types

from app.config import Settings, get_settings


@runtime_checkable
class LiveSessionProtocol(Protocol):
    """Protocol representing an active Live API bidirectional session."""

    async def send_realtime_input(
        self,
        *,
        audio: types.Blob | dict[str, Any] | None = None,
        activity_start: types.ActivityStart | dict[str, Any] | None = None,
        activity_end: types.ActivityEnd | dict[str, Any] | None = None,
    ) -> None:
        """Send realtime audio or activity signal to the Live session."""
        ...

    async def send(self, *, input: Any = None, end_of_turn: bool = True) -> None:
        """Send text or content turn to the Live session."""
        ...

    async def send_tool_response(
        self,
        *,
        function_responses: list[types.FunctionResponse | dict[str, Any]],
    ) -> None:
        """Send function/tool call response back to the Live session."""
        ...

    def receive(self) -> AsyncIterator[Any]:
        """Stream messages from the Live session."""
        ...

    async def close(self) -> None:
        """Close the Live session."""
        ...


class LiveClient:
    """Base interface for establishing Live API sessions."""

    @asynccontextmanager
    async def connect(
        self, model: str, config: dict[str, Any]
    ) -> AsyncIterator[LiveSessionProtocol]:
        """Establish a live session."""
        raise NotImplementedError
        yield  # type: ignore[unreachable]


class GenAILiveClient(LiveClient):
    """Production implementation using google-genai SDK (Developer API backend)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    @asynccontextmanager
    async def connect(
        self, model: str, config: dict[str, Any]
    ) -> AsyncIterator[LiveSessionProtocol]:
        client = self._get_client()
        async with client.aio.live.connect(model=model, config=config) as session:
            yield session  # type: ignore[misc]


def get_live_tools_config() -> list[dict[str, Any]]:
    """Return tool declarations for the Live API (Phase 3)."""
    return [
        {
            "function_declarations": [
                {
                    "name": "record_answer",
                    "description": (
                        "Record the student's answer to the question just asked. "
                        "Call exactly once per question, right after the student answers."
                    ),
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "question": {
                                "type": "STRING",
                                "description": "The question as asked",
                            },
                            "student_answer": {
                                "type": "STRING",
                                "description": "What the student said, paraphrased",
                            },
                            "correct": {"type": "BOOLEAN"},
                            "feedback": {
                                "type": "STRING",
                                "description": "One sentence of feedback",
                            },
                        },
                        "required": [
                            "question",
                            "student_answer",
                            "correct",
                            "feedback",
                        ],
                    },
                },
                {
                    "name": "end_quiz",
                    "description": (
                        "Call once after the final question has been recorded."
                    ),
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "summary": {
                                "type": "STRING",
                                "description": (
                                    "Two sentences summarizing strengths and what to review"
                                ),
                            }
                        },
                        "required": ["summary"],
                    },
                },
            ]
        }
    ]
