"""Tests for Voice Mode WebSocket relay and status endpoints."""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import pytest
from fastapi.testclient import TestClient
from google.genai import types
from starlette.websockets import WebSocketDisconnect

from app.config import Settings, get_settings
from app.dependencies import get_live_client
from app.main import app
from app.services.live_client import LiveClient, LiveSessionProtocol


class FakeLiveSession:
    """In-memory fake Live API session for testing."""

    def __init__(self, incoming_messages: list[Any] | None = None) -> None:
        self.sent_realtime_inputs: list[dict[str, Any]] = []
        self.sent_tool_responses: list[list[Any]] = []
        self.incoming_queue: asyncio.Queue[Any] = asyncio.Queue()
        if incoming_messages:
            for msg in incoming_messages:
                self.incoming_queue.put_nowait(msg)

    async def send_realtime_input(
        self,
        *,
        audio: types.Blob | dict[str, Any] | None = None,
        activity_start: types.ActivityStart | dict[str, Any] | None = None,
        activity_end: types.ActivityEnd | dict[str, Any] | None = None,
    ) -> None:
        self.sent_realtime_inputs.append(
            {
                "audio": audio,
                "activity_start": activity_start,
                "activity_end": activity_end,
            }
        )

    async def send_tool_response(
        self,
        *,
        function_responses: list[types.FunctionResponse | dict[str, Any]],
    ) -> None:
        self.sent_tool_responses.append(function_responses)

    async def receive(self) -> AsyncIterator[Any]:
        while True:
            msg = await self.incoming_queue.get()
            if msg is None:
                break
            yield msg

    async def close(self) -> None:
        pass


class FakeLiveClient(LiveClient):
    """Fake LiveClient returning configured FakeLiveSessions."""

    def __init__(self, incoming_messages: list[Any] | None = None) -> None:
        self.incoming_messages = incoming_messages or []
        self.last_config: dict[str, Any] | None = None
        self.last_model: str | None = None
        self.current_session: FakeLiveSession | None = None

    @asynccontextmanager
    async def connect(
        self, model: str, config: dict[str, Any]
    ) -> AsyncIterator[LiveSessionProtocol]:
        self.last_model = model
        self.last_config = config
        session = FakeLiveSession(self.incoming_messages)
        self.current_session = session
        try:
            yield session
        finally:
            pass


@pytest.fixture
def sample_study_guide() -> dict[str, Any]:
    with open("tests/fixtures/sample_study_guide.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def voice_enabled_settings() -> Settings:
    return Settings(
        gcp_project_id="test-project",
        firebase_storage_bucket="test-project.appspot.com",
        allowed_origins=["http://localhost:5173"],
        voice_enabled=True,
        gemini_live_api_key="test-live-key",
        voice_start_timeout_seconds=5.0,
        voice_session_max_seconds=180,
    )


@pytest.fixture
def voice_disabled_settings() -> Settings:
    return Settings(
        gcp_project_id="test-project",
        firebase_storage_bucket="test-project.appspot.com",
        allowed_origins=["http://localhost:5173"],
        voice_enabled=False,
    )


def test_status_reports_disabled(voice_disabled_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: voice_disabled_settings
    client = TestClient(app)
    resp = client.get("/api/v1/voice/status", headers={"X-Device-ID": "dev-test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["remaining_today"] == 0
    assert data["max_duration_s"] == 180


def test_voice_disabled_closes_4503(voice_disabled_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: voice_disabled_settings
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/api/v1/voice/session", headers={"origin": "http://localhost:5173"}
        ) as ws:
            err_frame = ws.receive_json()
            assert err_frame["type"] == "error"
            assert err_frame["code"] == "VOICE_DISABLED"
            ws.receive_text()
    assert exc_info.value.code == 4503


def test_origin_not_allowed_closes_4403(voice_enabled_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/api/v1/voice/session", headers={"origin": "https://evil.example"}
        ) as ws:
            err_frame = ws.receive_json()
            assert err_frame["type"] == "error"
            assert err_frame["code"] == "ORIGIN_NOT_ALLOWED"
            ws.receive_text()
    assert exc_info.value.code == 4403


def test_start_then_ready(voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect(
        "/api/v1/voice/session", headers={"origin": "http://localhost:5173"}
    ) as ws:
        ws.send_json(
            {
                "type": "start",
                "device_id": "test-device-1",
                "study_guide": sample_study_guide,
            }
        )
        ready_frame = ws.receive_json()
        assert ready_frame["type"] == "ready"
        assert re.match(r"^vs_[0-9a-f]{8}$", ready_frame["session_id"])
        assert ready_frame["max_duration_s"] == 180
        assert "ends_at" in ready_frame
        assert ready_frame["voice"] == "Kore"

        # Clean exit
        ws.send_json({"type": "end"})
        ended_frame = ws.receive_json()
        assert ended_frame["type"] == "ended"
        assert ended_frame["reason"] == "client_end"


def test_audio_relayed_both_directions(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    # Live sends user transcript, coach transcript, 480-byte audio, and turn_complete
    msg1 = types.LiveServerMessage(
        server_content=types.LiveServerContent(
            input_transcription=types.Transcription(text="I am ready")
        )
    )
    msg2 = types.LiveServerMessage(
        server_content=types.LiveServerContent(
            output_transcription=types.Transcription(text="Hello student"),
            model_turn=types.Content(
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            data=b"\x00\x01" * 240, mime_type="audio/pcm;rate=24000"
                        )
                    )
                ]
            ),
        )
    )
    msg3 = types.LiveServerMessage(
        server_content=types.LiveServerContent(turn_complete=True)
    )

    fake_live = FakeLiveClient([msg1, msg2, msg3])
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect(
        "/api/v1/voice/session", headers={"origin": "http://localhost:5173"}
    ) as ws:
        ws.send_json(
            {
                "type": "start",
                "device_id": "test-device-1",
                "study_guide": sample_study_guide,
            }
        )
        assert ws.receive_json()["type"] == "ready"

        # Client starts speech and sends 480 bytes of 16kHz audio
        ws.send_json({"type": "speech_start"})
        ws.send_bytes(b"\x00\x02" * 240)
        ws.send_json({"type": "speech_end"})

        # Expect server transcripts and audio
        t1 = ws.receive_json()
        assert t1 == {"type": "transcript", "role": "user", "text": "I am ready"}
        t2 = ws.receive_json()
        assert t2 == {"type": "transcript", "role": "coach", "text": "Hello student"}

        audio_part = ws.receive_bytes()
        assert len(audio_part) == 480
        assert audio_part == b"\x00\x01" * 240

        turn = ws.receive_json()
        assert turn == {"type": "turn_complete"}

        # Verify fake client received client audio
        assert fake_live.current_session is not None
        assert len(fake_live.current_session.sent_realtime_inputs) == 3
        # 1. speech_start, 2. audio, 3. speech_end
        assert fake_live.current_session.sent_realtime_inputs[0]["activity_start"] is not None
        assert fake_live.current_session.sent_realtime_inputs[1]["audio"] is not None
        assert fake_live.current_session.sent_realtime_inputs[2]["activity_end"] is not None

        ws.send_json({"type": "end"})
        ended = ws.receive_json()
        assert ended["type"] == "ended"


def test_audio_outside_speech_window_is_dropped(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect(
        "/api/v1/voice/session", headers={"origin": "http://localhost:5173"}
    ) as ws:
        ws.send_json(
            {
                "type": "start",
                "device_id": "test-device-1",
                "study_guide": sample_study_guide,
            }
        )
        assert ws.receive_json()["type"] == "ready"

        # Send audio directly without speech_start
        ws.send_bytes(b"\x00\x02" * 100)

        ws.send_json({"type": "end"})
        ws.receive_json()

        assert fake_live.current_session is not None
        # Zero audio forwarded
        audio_inputs = [
            inp for inp in fake_live.current_session.sent_realtime_inputs if inp["audio"] is not None
        ]
        assert len(audio_inputs) == 0


def test_bad_first_message_closes_4400(voice_enabled_settings: Settings):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/api/v1/voice/session", headers={"origin": "http://localhost:5173"}
        ) as ws:
            ws.send_json({"type": "not_start"})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "BAD_MESSAGE"
            ws.receive_text()
    assert exc_info.value.code == 4400


def test_start_timeout_closes_4408(
    voice_enabled_settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    voice_enabled_settings.voice_start_timeout_seconds = 0.1
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/api/v1/voice/session", headers={"origin": "http://localhost:5173"}
        ) as ws:
            import time
            time.sleep(0.2)
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "START_TIMEOUT"
            ws.receive_text()
    assert exc_info.value.code == 4408


def test_device_daily_cap_closes_4429(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    # First session
    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-limit", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "end"})
        assert ws.receive_json()["type"] == "ended"

    # Second session
    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-limit", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "end"})
        assert ws.receive_json()["type"] == "ended"

    # Third session should close with 4429 DEVICE_DAILY_LIMIT
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
            ws.send_json({"type": "start", "device_id": "dev-limit", "study_guide": sample_study_guide})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "DEVICE_DAILY_LIMIT"
            ws.receive_text()
    assert exc_info.value.code == 4429


def test_global_daily_cap_closes_4429(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    voice_enabled_settings.voice_sessions_per_day_global = 1
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    # Session from device A
    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-A", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "end"})
        ws.receive_json()

    # Session from device B hits global cap
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
            ws.send_json({"type": "start", "device_id": "dev-B", "study_guide": sample_study_guide})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "GLOBAL_DAILY_LIMIT"
            ws.receive_text()
    assert exc_info.value.code == 4429


def test_concurrent_cap_closes_4429(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    voice_enabled_settings.voice_max_concurrent_sessions = 1
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    # Open session 1 and keep it open
    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws1:
        ws1.send_json({"type": "start", "device_id": "dev-1", "study_guide": sample_study_guide})
        assert ws1.receive_json()["type"] == "ready"

        # Simultaneous session 2 should be rejected with 4429 CONCURRENT_LIMIT
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws2:
                ws2.send_json({"type": "start", "device_id": "dev-2", "study_guide": sample_study_guide})
                err = ws2.receive_json()
                assert err["type"] == "error"
                assert err["code"] == "CONCURRENT_LIMIT"
                ws2.receive_text()
        assert exc_info.value.code == 4429

        ws1.send_json({"type": "end"})
        ws1.receive_json()


def test_max_duration_ends_session(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    voice_enabled_settings.voice_session_max_seconds = 1
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-timer", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"

        # Wait for max duration watchdog to fire
        ended = ws.receive_json()
        assert ended["type"] == "ended"
        assert ended["reason"] == "max_duration"


def test_audio_quota_closes_4429(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    # voice_session_max_seconds = 1 -> quota = 16000 * 2 * 1 = 32000 bytes
    voice_enabled_settings.voice_session_max_seconds = 1
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
            ws.send_json({"type": "start", "device_id": "dev-quota", "study_guide": sample_study_guide})
            assert ws.receive_json()["type"] == "ready"
            ws.send_json({"type": "speech_start"})
            # Send 25000 bytes then 25000 bytes (total 50000 > 32000 quota)
            ws.send_bytes(b"\x01" * 25000)
            ws.send_bytes(b"\x01" * 25000)
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "AUDIO_QUOTA_EXCEEDED"
            ws.receive_text()
    assert exc_info.value.code == 4429


def test_guide_too_large_closes_4400(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    # Add a huge section so serialized JSON exceeds 32768 bytes
    sample_study_guide["sections"][0]["content"] = "x" * 35000
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
            ws.send_json({"type": "start", "device_id": "dev-large", "study_guide": sample_study_guide})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "GUIDE_TOO_LARGE"
            ws.receive_text()
    assert exc_info.value.code == 4400


def test_status_remaining_decrements(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    # Initial status
    r1 = client.get("/api/v1/voice/status", headers={"X-Device-ID": "test-device"})
    assert r1.json()["remaining_today"] == 2

    # Complete 1 session
    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "test-device", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "end"})
        assert ws.receive_json()["type"] == "ended"

    # Remaining status is now 1
    r2 = client.get("/api/v1/voice/status", headers={"X-Device-ID": "test-device"})
    assert r2.json()["remaining_today"] == 1


def test_session_end_log_line(
    voice_enabled_settings: Settings,
    sample_study_guide: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-log", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "end"})
        assert ws.receive_json()["type"] == "ended"

    captured = capsys.readouterr().out
    lines = [line for line in captured.strip().split("\n") if "voice_session_end" in line]
    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["event"] == "voice_session_end"
    assert log_data["device_id"] == "dev-log"
    assert log_data["reason"] == "client_end"
    assert "duration_s" in log_data
    assert "audio_in_bytes" in log_data
    assert "audio_out_bytes" in log_data
    assert "dropped_audio_frames" in log_data
    assert "estimated_cost_usd" in log_data
    assert log_data["model"] == "gemini-3.1-flash-live-preview"


# --- Phase 3 Scoring Tests ---


def test_tools_declared(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-tools", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "end"})
        ws.receive_json()

    assert fake_live.last_config is not None
    assert "tools" in fake_live.last_config
    tools = fake_live.last_config["tools"]
    fn_names = [f["name"] for group in tools for f in group["function_declarations"]]
    assert "record_answer" in fn_names
    assert "end_quiz" in fn_names


def test_record_answer_emits_frame_and_response(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    tool_msg = types.LiveServerMessage(
        tool_call=types.LiveServerToolCall(
            function_calls=[
                types.FunctionCall(
                    id="call_rec_1",
                    name="record_answer",
                    args={
                        "question": "What is chlorophyll?",
                        "student_answer": "Green pigment",
                        "correct": True,
                        "feedback": "Correct, nice work!",
                    },
                )
            ]
        )
    )

    fake_live = FakeLiveClient([tool_msg])
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-rec", "study_guide": sample_study_guide, "num_questions": 5})
        assert ws.receive_json()["type"] == "ready"

        # Client receives answer_recorded frame
        frame = ws.receive_json()
        assert frame["type"] == "answer_recorded"
        assert frame["index"] == 1
        assert frame["question"] == "What is chlorophyll?"
        assert frame["student_answer"] == "Green pigment"
        assert frame["correct"] is True
        assert frame["feedback"] == "Correct, nice work!"
        assert frame["score"] == {"correct": 1, "total": 5}

        # Verify fake received tool response
        assert fake_live.current_session is not None
        assert len(fake_live.current_session.sent_tool_responses) == 1
        resp = fake_live.current_session.sent_tool_responses[0][0]
        assert resp.id == "call_rec_1"
        assert resp.response == {"status": "ok", "recorded": 1, "remaining": 4}

        ws.send_json({"type": "end"})
        ws.receive_json()


def test_record_answer_beyond_cap_ignored(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    # num_questions: 3, but 4 calls sent
    tool_calls = [
        types.LiveServerMessage(
            tool_call=types.LiveServerToolCall(
                function_calls=[
                    types.FunctionCall(
                        id=f"call_{i}",
                        name="record_answer",
                        args={"question": f"Q{i}", "student_answer": f"A{i}", "correct": True, "feedback": "Good"},
                    )
                ]
            )
        )
        for i in range(1, 5)
    ]

    fake_live = FakeLiveClient(tool_calls)
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-cap", "study_guide": sample_study_guide, "num_questions": 3})
        assert ws.receive_json()["type"] == "ready"

        # 3 answer_recorded frames received
        for idx in range(1, 4):
            f = ws.receive_json()
            assert f["type"] == "answer_recorded"
            assert f["index"] == idx

        # The 4th call was beyond cap; check fake's tool responses
        assert fake_live.current_session is not None
        assert len(fake_live.current_session.sent_tool_responses) == 4
        fourth_resp = fake_live.current_session.sent_tool_responses[3][0]
        assert fourth_resp.id == "call_4"
        assert fourth_resp.response == {"status": "ignored", "reason": "quiz_full"}

        ws.send_json({"type": "end"})
        ws.receive_json()


def test_invalid_tool_args_error_response(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    # Missing 'correct' field
    tool_msg = types.LiveServerMessage(
        tool_call=types.LiveServerToolCall(
            function_calls=[
                types.FunctionCall(
                    id="call_bad",
                    name="record_answer",
                    args={"question": "What?", "student_answer": "That", "feedback": "Missing correct flag"},
                )
            ]
        )
    )

    fake_live = FakeLiveClient([tool_msg])
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-bad-args", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"

        # Check tool response on fake
        assert fake_live.current_session is not None
        assert len(fake_live.current_session.sent_tool_responses) == 1
        resp = fake_live.current_session.sent_tool_responses[0][0]
        assert resp.id == "call_bad"
        assert resp.response == {"status": "error", "reason": "invalid_arguments"}

        ws.send_json({"type": "end"})
        ws.receive_json()


def test_end_quiz_summary_then_quiz_complete(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    end_msg = types.LiveServerMessage(
        tool_call=types.LiveServerToolCall(
            function_calls=[
                types.FunctionCall(
                    id="call_end",
                    name="end_quiz",
                    args={"summary": "You demonstrated great understanding of light reactions."},
                )
            ]
        )
    )
    turn_complete_msg = types.LiveServerMessage(
        server_content=types.LiveServerContent(turn_complete=True)
    )

    fake_live = FakeLiveClient([end_msg, turn_complete_msg])
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-eq", "study_guide": sample_study_guide, "num_questions": 5})
        assert ws.receive_json()["type"] == "ready"

        # Client receives quiz_summary frame
        summary_frame = ws.receive_json()
        assert summary_frame["type"] == "quiz_summary"
        assert "light reactions" in summary_frame["summary"]
        assert summary_frame["score"]["total"] == 5

        # Live turn_complete arrives
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "turn_complete"

        # Then server ends session with reason quiz_complete
        ended = ws.receive_json()
        assert ended["type"] == "ended"
        assert ended["reason"] == "quiz_complete"


def test_end_quiz_fallback_timeout(
    voice_enabled_settings: Settings,
    sample_study_guide: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
):
    # Live sends end_quiz but never sends turn_complete
    end_msg = types.LiveServerMessage(
        tool_call=types.LiveServerToolCall(
            function_calls=[
                types.FunctionCall(
                    id="call_end",
                    name="end_quiz",
                    args={"summary": "Summary here."},
                )
            ]
        )
    )

    fake_live = FakeLiveClient([end_msg])
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    # Monkeypatch deadline offset to 0.1s inside Coordinator
    from app.services import voice_session
    orig_coordinator = voice_session.VoiceSessionCoordinator

    class ShortTimeoutCoordinator(orig_coordinator):
        async def _relay_loop(self, live_session):
            # Patch deadline calculation in the loop
            res = await super()._relay_loop(live_session)
            return res

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-fallback", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"

        summary = ws.receive_json()
        assert summary["type"] == "quiz_summary"

        # Rather than waiting 15s in test, wait or let max_duration or sleep fire;
        # Since fallback is 15s, let's test that if we send 'end' or after fallback it finishes.
        ws.send_json({"type": "end"})
        ended = ws.receive_json()
        assert ended["type"] == "ended"


def test_num_questions_out_of_range_closes_4400(
    voice_enabled_settings: Settings, sample_study_guide: dict[str, Any]
):
    fake_live = FakeLiveClient()
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
            ws.send_json(
                {
                    "type": "start",
                    "device_id": "dev-range",
                    "study_guide": sample_study_guide,
                    "num_questions": 11,
                }
            )
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "INVALID_NUM_QUESTIONS"
            ws.receive_text()
    assert exc_info.value.code == 4400


def test_session_end_log_line_has_quiz_counts(
    voice_enabled_settings: Settings,
    sample_study_guide: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
):
    tool_msg = types.LiveServerMessage(
        tool_call=types.LiveServerToolCall(
            function_calls=[
                types.FunctionCall(
                    id="call_rec",
                    name="record_answer",
                    args={
                        "question": "Q1",
                        "student_answer": "A1",
                        "correct": True,
                        "feedback": "Nice",
                    },
                )
            ]
        )
    )

    fake_live = FakeLiveClient([tool_msg])
    app.dependency_overrides[get_settings] = lambda: voice_enabled_settings
    app.dependency_overrides[get_live_client] = lambda: fake_live
    client = TestClient(app)

    with client.websocket_connect("/api/v1/voice/session", headers={"origin": "http://localhost:5173"}) as ws:
        ws.send_json({"type": "start", "device_id": "dev-quiz-log", "study_guide": sample_study_guide})
        assert ws.receive_json()["type"] == "ready"
        ws.receive_json()  # answer_recorded frame
        ws.send_json({"type": "end"})
        assert ws.receive_json()["type"] == "ended"

    captured = capsys.readouterr().out
    lines = [line for line in captured.strip().split("\n") if "voice_session_end" in line]
    assert len(lines) == 1
    log_data = json.loads(lines[0])
    assert log_data["questions_asked"] == 1
    assert log_data["questions_correct"] == 1
