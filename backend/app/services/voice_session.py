"""Voice session coordinator and WebSocket relay logic."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from google.genai import types
import websockets
import websockets.exceptions

from app.config import Settings
from app.models.responses import StudyGuide
from app.services.live_client import LiveClient, LiveSessionProtocol, get_live_tools_config
from app.services.voice_guard import VoiceCapError, VoiceSessionGuard

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "voice_coach_template.txt"

# Sent to the coach after the pause that follows its feedback on an answer.
NEXT_QUESTION_PROMPT = (
    "Continue. If you have not yet spoken your feedback on the student's last answer, "
    "say it now, starting with a clear verdict. Then ask the next question. "
    "If you already asked it, repeat it briefly."
)


def _render_prompt(guide: StudyGuide, num_questions: int) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    sections_lines = []
    for s in guide.sections:
        sections_lines.append(f"## {s.heading}\n{s.content}")
        if s.key_terms:
            for kt in s.key_terms:
                sections_lines.append(f"- {kt.term}: {kt.definition}")
    guide_sections = "\n\n".join(sections_lines)

    return template.format(
        guide_title=guide.title,
        guide_summary=guide.summary,
        guide_sections=guide_sections,
        num_questions=num_questions,
    )


class VoiceSessionCoordinator:
    """Manages the lifecycle, relaying, caps, and logging for a single voice session."""

    def __init__(
        self,
        websocket: WebSocket,
        live_client: LiveClient,
        guard: VoiceSessionGuard,
        settings: Settings,
    ) -> None:
        self.websocket = websocket
        self.live_client = live_client
        self.guard = guard
        self.settings = settings

        # Session attributes
        self.session_id = f"vs_{secrets.token_hex(4)}"
        self.device_id = ""
        self.study_guide: StudyGuide | None = None
        self.voice = settings.voice_coach_voice
        self.num_questions = settings.voice_quiz_questions
        self.max_duration_s = settings.voice_session_max_seconds

        # Accounting / state
        self.start_time = 0.0
        self.in_speech = False
        self.audio_in_bytes = 0
        self.audio_out_bytes = 0
        self.dropped_audio_frames = 0
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None
        self.questions_asked = 0
        self.questions_correct = 0
        self.recorded_answers: list[dict[str, Any]] = []
        self.end_quiz_received = False
        self.ended_reason = "client_end"
        # Pacing and time-limit state
        self.input_locked = False  # True once the time limit is reached
        self.model_speaking = False  # audio received since the last turn_complete
        self.awaiting_response = False  # student finished speaking, coach hasn't completed a turn
        self.answer_recorded_this_turn = False

    async def _send_error_and_close(self, code: int, error_code: str, message: str) -> None:
        try:
            await self.websocket.send_text(
                json.dumps({"type": "error", "code": error_code, "message": message})
            )
        except Exception:
            pass
        try:
            await self.websocket.close(code=code)
        except Exception:
            pass

    async def run(self) -> None:
        """Run the session lifecycle."""
        # 1. Check origin handshake
        origin = self.websocket.headers.get("origin")
        if self.settings.allowed_origins:
            if not origin or origin not in self.settings.allowed_origins:
                await self.websocket.accept()
                await self._send_error_and_close(4403, "ORIGIN_NOT_ALLOWED", "Origin not allowed")
                return

        # 2. Check feature flag
        if not self.settings.voice_enabled:
            await self.websocket.accept()
            await self._send_error_and_close(
                4503, "VOICE_DISABLED", "Voice mode is turned off right now."
            )
            return

        # Accept websocket connection
        await self.websocket.accept()

        # 3. Wait for start message within timeout
        try:
            start_raw = await asyncio.wait_for(
                self.websocket.receive(),
                timeout=self.settings.voice_start_timeout_seconds,
            )
        except asyncio.TimeoutError:
            await self._send_error_and_close(
                4408,
                "START_TIMEOUT",
                "The connection timed out before the session started.",
            )
            return

        if "text" not in start_raw or not start_raw["text"]:
            await self._send_error_and_close(4400, "BAD_MESSAGE", "Malformed start frame")
            return

        try:
            start_msg = json.loads(start_raw["text"])
        except Exception:
            await self._send_error_and_close(4400, "BAD_MESSAGE", "Malformed JSON in start frame")
            return

        if not isinstance(start_msg, dict) or start_msg.get("type") != "start":
            await self._send_error_and_close(4400, "BAD_MESSAGE", "First frame must be start")
            return

        # Validate device_id
        dev_id = start_msg.get("device_id")
        if not dev_id or not isinstance(dev_id, str) or len(dev_id) > 64:
            await self._send_error_and_close(4401, "INVALID_DEVICE_ID", "Invalid device_id")
            return
        self.device_id = dev_id

        # Validate study_guide
        guide_data = start_msg.get("study_guide")
        if not guide_data:
            await self._send_error_and_close(
                4400, "INVALID_STUDY_GUIDE", "Missing study_guide in start frame"
            )
            return

        serialized_guide = json.dumps(guide_data).encode("utf-8")
        if len(serialized_guide) > self.settings.voice_max_guide_bytes:
            await self._send_error_and_close(
                4400, "GUIDE_TOO_LARGE", "Study guide exceeds maximum allowed size"
            )
            return

        try:
            self.study_guide = StudyGuide.model_validate(guide_data)
        except Exception as e:
            await self._send_error_and_close(
                4400, "INVALID_STUDY_GUIDE", f"Invalid study guide: {e}"
            )
            return

        # Validate voice
        if "voice" in start_msg and start_msg["voice"]:
            if start_msg["voice"] not in self.settings.voice_allowed_voices:
                await self._send_error_and_close(
                    4400, "INVALID_VOICE", f"Voice '{start_msg['voice']}' is not allowed"
                )
                return
            self.voice = start_msg["voice"]

        # Validate num_questions (Phase 3)
        if "num_questions" in start_msg:
            nq = start_msg["num_questions"]
            if not isinstance(nq, int) or nq < 3 or nq > 10:
                await self._send_error_and_close(
                    4400, "INVALID_NUM_QUESTIONS", "num_questions must be an integer between 3 and 10"
                )
                return
            self.num_questions = nq

        # Acquire guard
        try:
            await self.guard.acquire(self.device_id, self.settings)
        except VoiceCapError as e:
            await self._send_error_and_close(e.close_code, e.error_code, e.message)
            return

        # Prepare Live session config
        rendered_prompt = _render_prompt(self.study_guide, self.num_questions)
        live_config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": rendered_prompt,
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": self.voice}}
            },
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "realtime_input_config": {
                "automatic_activity_detection": {"disabled": True}
            },
            "tools": get_live_tools_config(),
        }

        self.start_time = time.monotonic()
        ends_at = (
            datetime.now(timezone.utc) + timedelta(seconds=self.max_duration_s)
        ).isoformat()

        clean_exit = False
        try:
            async with self.live_client.connect(
                model=self.settings.gemini_live_model, config=live_config
            ) as live_session:
                # Send ready frame
                await self.websocket.send_text(
                    json.dumps(
                        {
                            "type": "ready",
                            "session_id": self.session_id,
                            "max_duration_s": self.max_duration_s,
                            "ends_at": ends_at,
                            "voice": self.voice,
                        }
                    )
                )

                # Run relay loop
                clean_exit = await self._relay_loop(live_session)

        except WebSocketDisconnect:
            self.ended_reason = "client_end"
        except VoiceCapError as e:
            await self._send_error_and_close(e.close_code, e.error_code, e.message)
            return
        except Exception as e:
            logger.exception("Upstream or relay error in voice session %s", self.session_id)
            await self._send_error_and_close(1011, "UPSTREAM_ERROR", f"Voice service error: {e}")
            return
        finally:
            refund = self.ended_reason in ("upstream_closed", "error", "connection_error")
            await self.guard.release(self.device_id, refund=refund)
            self._log_session_end()

        if clean_exit:
            try:
                await self.websocket.send_text(
                    json.dumps({"type": "ended", "reason": self.ended_reason})
                )
                await self.websocket.close(code=1000)
            except Exception:
                pass

    async def _relay_loop(self, live_session: LiveSessionProtocol) -> bool:
        """Run concurrent client-to-live, live-to-client, and max-duration tasks.

        Returns:
            True if session ended normally (send 'ended' and close 1000), False otherwise.
        """
        end_event = asyncio.Event()
        quiz_complete_deadline: float | None = None
        grace_deadline: float | None = None
        nudge_task: asyncio.Task[None] | None = None

        async def nudge_next_question() -> None:
            """After a pause, ask the coach to move on to the next question."""
            try:
                await asyncio.sleep(self.settings.voice_next_question_pause_seconds)
            except asyncio.CancelledError:
                return
            if end_event.is_set() or self.input_locked or self.end_quiz_received:
                return
            try:
                if hasattr(live_session, "send"):
                    await live_session.send(input=NEXT_QUESTION_PROMPT, end_of_turn=True)
            except Exception as e:
                logger.warning("Failed to send next-question nudge: %s", e)

        def cancel_nudge() -> None:
            nonlocal nudge_task
            if nudge_task is not None and not nudge_task.done():
                nudge_task.cancel()
            nudge_task = None

        async def client_to_live_task() -> None:
            while not end_event.is_set():
                try:
                    frame = await asyncio.wait_for(
                        self.websocket.receive(),
                        timeout=self.settings.voice_idle_timeout_seconds,
                    )
                except (asyncio.TimeoutError, TimeoutError):
                    self.ended_reason = "idle_timeout"
                    end_event.set()
                    break
                except WebSocketDisconnect:
                    self.ended_reason = "client_end"
                    end_event.set()
                    break
                except RuntimeError as e:
                    if "disconnect" in str(e).lower():
                        self.ended_reason = "client_end"
                        end_event.set()
                        break
                    raise

                if "text" in frame and frame["text"] is not None:
                    try:
                        msg = json.loads(frame["text"])
                    except Exception:
                        await self._send_error_and_close(4400, "BAD_MESSAGE", "Invalid JSON")
                        raise VoiceCapError(4400, "BAD_MESSAGE", "Invalid JSON")

                    msg_type = msg.get("type")
                    if msg_type == "speech_start":
                        if self.input_locked:
                            continue
                        if not self.in_speech:
                            # The student is answering; do not interrupt with a nudge.
                            cancel_nudge()
                            self.in_speech = True
                            await live_session.send_realtime_input(
                                activity_start=types.ActivityStart()
                            )
                    elif msg_type == "speech_end":
                        if self.in_speech:
                            self.in_speech = False
                            self.awaiting_response = True
                            await live_session.send_realtime_input(
                                activity_end=types.ActivityEnd()
                            )
                    elif msg_type == "end":
                        self.ended_reason = "client_end"
                        end_event.set()
                        break
                    else:
                        await self._send_error_and_close(
                            4400, "BAD_MESSAGE", f"Unknown message type: {msg_type}"
                        )
                        raise VoiceCapError(4400, "BAD_MESSAGE", "Unknown message type")

                elif "bytes" in frame and frame["bytes"] is not None:
                    chunk = frame["bytes"]
                    if len(chunk) > 32768:
                        await self._send_error_and_close(
                            4400, "FRAME_TOO_LARGE", "Audio frame exceeds 32768 bytes"
                        )
                        raise VoiceCapError(4400, "FRAME_TOO_LARGE", "Frame too large")

                    if not self.in_speech or self.input_locked:
                        self.dropped_audio_frames += 1
                        continue

                    if self.audio_in_bytes + len(chunk) > self.settings.voice_audio_quota_bytes:
                        await self._send_error_and_close(
                            4429, "AUDIO_QUOTA_EXCEEDED", "Inbound audio byte quota exceeded"
                        )
                        raise VoiceCapError(4429, "AUDIO_QUOTA_EXCEEDED", "Quota exceeded")

                    self.audio_in_bytes += len(chunk)
                    await live_session.send_realtime_input(
                        audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                    )

        async def live_to_client_task() -> None:
            nonlocal quiz_complete_deadline, nudge_task
            try:
                while not end_event.is_set():
                    has_messages = False
                    try:
                        async for msg in live_session.receive():
                            has_messages = True
                            if end_event.is_set():
                                break

                            # Usage metadata
                            if getattr(msg, "usage_metadata", None):
                                meta = msg.usage_metadata
                                if getattr(meta, "prompt_token_count", None) is not None:
                                    self.input_tokens = meta.prompt_token_count
                                if getattr(meta, "response_token_count", None) is not None:
                                    self.output_tokens = meta.response_token_count

                            # Server content
                            if getattr(sc := getattr(msg, "server_content", None), "model_turn", None) or sc:
                                # Transcriptions first
                                if getattr(sc, "input_transcription", None) and sc.input_transcription.text:
                                    await self.websocket.send_text(
                                        json.dumps(
                                            {
                                                "type": "transcript",
                                                "role": "user",
                                                "text": sc.input_transcription.text,
                                            }
                                        )
                                    )

                                if (
                                    getattr(sc, "output_transcription", None)
                                    and sc.output_transcription.text
                                ):
                                    await self.websocket.send_text(
                                        json.dumps(
                                            {
                                                "type": "transcript",
                                                "role": "coach",
                                                "text": sc.output_transcription.text,
                                            }
                                        )
                                    )

                                # Model turn parts (audio / text)
                                if getattr(sc, "model_turn", None) and sc.model_turn.parts:
                                    for part in sc.model_turn.parts:
                                        if getattr(part, "inline_data", None) and part.inline_data.data:
                                            data = part.inline_data.data
                                            self.audio_out_bytes += len(data)
                                            self.model_speaking = True
                                            await self.websocket.send_bytes(data)

                                if getattr(sc, "turn_complete", False):
                                    self.model_speaking = False
                                    self.awaiting_response = False
                                    await self.websocket.send_text(json.dumps({"type": "turn_complete"}))
                                    if self.end_quiz_received:
                                        self.ended_reason = "quiz_complete"
                                        end_event.set()
                                        break
                                    if self.input_locked:
                                        # Time was up; the coach has finished its turn.
                                        self.ended_reason = "max_duration"
                                        end_event.set()
                                        break
                                    if self.answer_recorded_this_turn:
                                        self.answer_recorded_this_turn = False
                                        cancel_nudge()
                                        nudge_task = asyncio.create_task(nudge_next_question())

                                if getattr(sc, "interrupted", False):
                                    await self.websocket.send_text(json.dumps({"type": "interrupted"}))

                            # Tool call (Phase 3)
                            if getattr(msg, "tool_call", None) and msg.tool_call.function_calls:
                                responses = []
                                for fc in msg.tool_call.function_calls:
                                    fc_id = getattr(fc, "id", "")
                                    fc_name = getattr(fc, "name", "")
                                    fc_args = getattr(fc, "args", {}) or {}

                                    if fc_name == "record_answer":
                                        # Validate args
                                        q = fc_args.get("question")
                                        sa = fc_args.get("student_answer")
                                        c = fc_args.get("correct")
                                        fb = fc_args.get("feedback")

                                        if not all([isinstance(q, str), isinstance(sa, str), isinstance(c, bool), isinstance(fb, str)]):
                                            responses.append(
                                                types.FunctionResponse(
                                                    id=fc_id,
                                                    name=fc_name,
                                                    response={"status": "error", "reason": "invalid_arguments"},
                                                )
                                            )
                                        elif len(self.recorded_answers) >= self.num_questions:
                                            responses.append(
                                                types.FunctionResponse(
                                                    id=fc_id,
                                                    name=fc_name,
                                                    response={"status": "ignored", "reason": "quiz_full"},
                                                )
                                            )
                                        else:
                                            self.questions_asked += 1
                                            if c:
                                                self.questions_correct += 1
                                            idx = len(self.recorded_answers) + 1
                                            rec = {
                                                "index": idx,
                                                "question": q,
                                                "student_answer": sa,
                                                "correct": c,
                                                "feedback": fb,
                                            }
                                            self.recorded_answers.append(rec)
                                            self.answer_recorded_this_turn = True
                                            # Client frame
                                            await self.websocket.send_text(
                                                json.dumps(
                                                    {
                                                        "type": "answer_recorded",
                                                        "index": idx,
                                                        "question": q,
                                                        "student_answer": sa,
                                                        "correct": c,
                                                        "feedback": fb,
                                                        "score": {
                                                            "correct": self.questions_correct,
                                                            "total": self.num_questions,
                                                        },
                                                    }
                                                )
                                            )
                                            responses.append(
                                                types.FunctionResponse(
                                                    id=fc_id,
                                                    name=fc_name,
                                                    response={
                                                        "status": "ok",
                                                        "recorded": idx,
                                                        "remaining": self.num_questions - idx,
                                                    },
                                                )
                                            )

                                    elif fc_name == "end_quiz":
                                        summary = fc_args.get("summary")
                                        if not summary or not isinstance(summary, str):
                                            responses.append(
                                                types.FunctionResponse(
                                                    id=fc_id,
                                                    name=fc_name,
                                                    response={"status": "error", "reason": "invalid_arguments"},
                                                )
                                            )
                                        else:
                                            self.end_quiz_received = True
                                            quiz_complete_deadline = time.monotonic() + 15.0
                                            await self.websocket.send_text(
                                                json.dumps(
                                                    {
                                                        "type": "quiz_summary",
                                                        "summary": summary,
                                                        "score": {
                                                            "correct": self.questions_correct,
                                                            "asked": self.questions_asked,
                                                            "total": self.num_questions,
                                                        },
                                                    }
                                                )
                                            )
                                            responses.append(
                                                types.FunctionResponse(
                                                    id=fc_id,
                                                    name=fc_name,
                                                    response={"status": "ok"},
                                                )
                                            )

                                if responses:
                                    await live_session.send_tool_response(function_responses=responses)
                    except (websockets.exceptions.ConnectionClosed, ConnectionResetError):
                        break

                    if not has_messages or getattr(live_session, "is_closed", False):
                        break

                # Upstream stream ended
                if not end_event.is_set():
                    self.ended_reason = "upstream_closed"
                    end_event.set()

            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Live stream error")
                raise

        async def max_duration_watchdog() -> None:
            nonlocal quiz_complete_deadline, grace_deadline
            while not end_event.is_set():
                now = time.monotonic()
                elapsed = now - self.start_time
                if elapsed >= self.max_duration_s and not self.input_locked:
                    # Time is up: stop taking input, but let the coach finish
                    # the turn it is in (or the reply it owes) within a grace
                    # window rather than cutting it off mid-sentence.
                    self.input_locked = True
                    cancel_nudge()
                    grace_deadline = now + self.settings.voice_end_grace_seconds
                    if self.in_speech:
                        self.in_speech = False
                        self.awaiting_response = True
                        try:
                            await live_session.send_realtime_input(activity_end=types.ActivityEnd())
                        except Exception:
                            pass
                    try:
                        await self.websocket.send_text(
                            json.dumps(
                                {
                                    "type": "time_up",
                                    "grace_s": self.settings.voice_end_grace_seconds,
                                }
                            )
                        )
                    except Exception:
                        pass
                    if not self.model_speaking and not self.awaiting_response:
                        self.ended_reason = "max_duration"
                        end_event.set()
                        break

                if grace_deadline is not None and now >= grace_deadline:
                    self.ended_reason = "max_duration"
                    end_event.set()
                    break

                if quiz_complete_deadline is not None and now >= quiz_complete_deadline:
                    self.ended_reason = "quiz_complete"
                    end_event.set()
                    break

                await asyncio.sleep(0.05)

        t_client = asyncio.create_task(client_to_live_task())
        t_live = asyncio.create_task(live_to_client_task())
        t_timer = asyncio.create_task(max_duration_watchdog())

        # Proactively prompt the coach to greet and ask Question 1 out loud
        try:
            if hasattr(live_session, "send"):
                await live_session.send(
                    input="Start the oral quiz now. Introduce the quiz in one sentence and ask Question 1 out loud.",
                    end_of_turn=True,
                )
        except Exception as e:
            logger.warning("Failed to send initial kickoff prompt: %s", e)

        done, pending = await asyncio.wait(
            [t_client, t_live, t_timer],
            return_when=asyncio.FIRST_COMPLETED,
        )

        cancel_nudge()
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        # Check if an exception was raised in any completed task
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (asyncio.CancelledError, WebSocketDisconnect)):
                raise exc

        return True

    def _log_session_end(self) -> None:
        duration_s = round(time.monotonic() - self.start_time, 1) if self.start_time else 0.0

        if self.input_tokens is not None and self.output_tokens is not None:
            cost = (
                (self.input_tokens / 1_000_000) * self.settings.voice_audio_in_price_per_m
                + (self.output_tokens / 1_000_000) * self.settings.voice_audio_out_price_per_m
            )
        else:
            in_sec = self.audio_in_bytes / (16000 * 2)
            out_sec = self.audio_out_bytes / (24000 * 2)
            in_tok = in_sec * 25
            out_tok = out_sec * 25
            cost = (
                (in_tok / 1_000_000) * self.settings.voice_audio_in_price_per_m
                + (out_tok / 1_000_000) * self.settings.voice_audio_out_price_per_m
            )

        log_payload = {
            "event": "voice_session_end",
            "session_id": self.session_id,
            "device_id": self.device_id,
            "reason": self.ended_reason,
            "duration_s": duration_s,
            "audio_in_bytes": self.audio_in_bytes,
            "audio_out_bytes": self.audio_out_bytes,
            "dropped_audio_frames": self.dropped_audio_frames,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": round(cost, 4),
            "model": self.settings.gemini_live_model,
            "questions_asked": self.questions_asked,
            "questions_correct": self.questions_correct,
        }

        # Print single structured JSON object to stdout as required by spec
        sys.stdout.write(json.dumps(log_payload) + "\n")
        sys.stdout.flush()
