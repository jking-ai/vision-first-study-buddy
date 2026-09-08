# Voice Mode Phase 1: Backend WebSocket Relay — Design Spec

**Date:** 2026-09-08
**Phase:** 4.1 — Voice Coach backend
**Part of:** [Voice Mode overview](2026-09-08-voice-mode-overview.md)

---

## What This Phase Delivers

A WebSocket endpoint on the existing FastAPI backend that opens a Gemini Live API session per client, relays push-to-talk audio in both directions with transcripts, and enforces per-session, per-device, global, and concurrency caps. Plus a status endpoint the frontend uses to show remaining sessions.

**Why:** Every later phase consumes this protocol, and the spend caps must exist before any browser can reach the Live API.

## Architecture

```
Browser ──WS──► /api/v1/voice/session (FastAPI, Cloud Run)
                  │ 1. accept, wait ≤5s for {"type":"start"}
                  │ 2. VoiceSessionGuard.acquire(device_id) → 4429 on cap
                  │ 3. LiveClient.connect(model, config(system_instruction))
                  │ 4. two tasks: client→live (audio, activity), live→client (audio, transcripts, events)
                  │ 5. end on: client "end", max_duration, idle_timeout, upstream close
                  │ 6. VoiceSessionGuard.release(); log voice_session_end
                  └──WSS──► generativelanguage.googleapis.com (google-genai, api_key)

Browser ──GET──► /api/v1/voice/status (X-Device-ID) → enabled, caps, remaining_today
```

## Requirements

1. New WebSocket route `WS /api/v1/voice/session` mounted under the existing `/api/v1` prefix in `backend/app/main.py:51-55`.
2. New route `GET /api/v1/voice/status` returning the caps and the device's remaining sessions for the current UTC day.
3. Client protocol and server protocol exactly as defined in Contracts. Control messages are JSON text frames. Audio is binary frames.
4. The Live session is configured for audio output, manual activity detection, input and output transcription, and a system instruction built from `backend/app/prompts/voice_coach_template.txt` with the client-supplied study guide interpolated.
5. Caps enforced server-side, all configurable (see Config): session duration, sessions per device per UTC day, sessions per UTC day globally, concurrent sessions, idle timeout, inbound audio byte quota, study guide payload size.
6. Origin check on the WebSocket handshake: when `settings.allowed_origins` is non-empty, an `Origin` header not in the list closes with 4403 before any Live connection is opened.
7. One structured JSON log line per ended session (see Contracts, log line).
8. Feature flag `VOICE_ENABLED` defaulting to `false`. When false the status endpoint reports `enabled: false` and the WebSocket closes with 4503 immediately after accept.
9. All Live API calls go through a `LiveClient` abstraction injected via a FastAPI dependency so tests substitute a fake (same pattern as `_cached_gemini_client` / `get_gemini_client` in `backend/app/dependencies.py:25-37`).

**Permissions:** No user accounts. Device identity is the `device_id` field of the `start` message (browsers cannot set `X-Device-ID` on a WebSocket handshake). Same validation as `get_device_id` in `backend/app/dependencies.py:65-82`: non-empty, at most 64 characters.

**Error behavior:** Every failure sends one `{"type":"error","code":...,"message":...}` text frame (when the socket is still open) and then closes with the code in the table below. Upstream Live API exceptions map to `UPSTREAM_ERROR` / 1011. No retries of the Live connection inside a session.

## Contracts

### WebSocket `WS /api/v1/voice/session`

Handshake: no query parameters, no custom headers required. Subprotocol: none.

**Client → server messages**

| Frame | Shape | Rules |
|---|---|---|
| text | `{"type":"start","device_id":"<1..64 chars>","study_guide":<StudyGuide JSON>,"voice":"<optional voice name>"}` | Must be the first frame and arrive within `VOICE_START_TIMEOUT_SECONDS` of accept. `study_guide` must validate as `StudyGuide` (`backend/app/models/responses.py:54`). Serialized `study_guide` must be at most `VOICE_MAX_GUIDE_BYTES`. `voice` defaults to `VOICE_COACH_VOICE`; any value not in `VOICE_ALLOWED_VOICES` is rejected. |
| text | `{"type":"speech_start"}` | Forwarded as `ActivityStart`. Ignored with no error if already in speech. |
| binary | raw PCM16 LE, 16 kHz, mono; at most 32768 bytes per frame | Forwarded as `send_realtime_input(audio=Blob(data, mime_type="audio/pcm;rate=16000"))`. Frames received outside a `speech_start`/`speech_end` window are dropped and counted in the log line as `dropped_audio_frames`. A frame over 32768 bytes closes with 4400 `FRAME_TOO_LARGE`. |
| text | `{"type":"speech_end"}` | Forwarded as `ActivityEnd`. |
| text | `{"type":"end"}` | Server sends `ended` with reason `client_end` and closes 1000. |
| text | any other `type` | Close 4400 `BAD_MESSAGE`. |

**Server → client messages**

| Frame | Shape | When |
|---|---|---|
| text | `{"type":"ready","session_id":"vs_<8 hex>","max_duration_s":<int>,"ends_at":"<ISO 8601 UTC>","voice":"<name>"}` | After the Live session is open. |
| binary | raw PCM16 LE, 24 kHz, mono | Every audio part received from the Live session, in order. |
| text | `{"type":"transcript","role":"user","text":"<string>"}` | Every `input_transcription` chunk. |
| text | `{"type":"transcript","role":"coach","text":"<string>"}` | Every `output_transcription` chunk. |
| text | `{"type":"turn_complete"}` | `server_content.turn_complete` is true. |
| text | `{"type":"interrupted"}` | `server_content.interrupted` is true. |
| text | `{"type":"error","code":"<CODE>","message":"<string>"}` | Before an error close. |
| text | `{"type":"ended","reason":"client_end"\|"max_duration"\|"idle_timeout"\|"upstream_closed"}` | Before a normal close. |

**Close codes**

| Code | Error code in preceding frame | Condition |
|---|---|---|
| 1000 | none | Normal end after `ended`. |
| 1011 | `UPSTREAM_ERROR` | Live API raised or closed unexpectedly. `ended` is not sent. |
| 4400 | `BAD_MESSAGE`, `FRAME_TOO_LARGE`, `INVALID_STUDY_GUIDE`, `GUIDE_TOO_LARGE`, `INVALID_VOICE` | Malformed or oversize client input. |
| 4401 | `INVALID_DEVICE_ID` | `device_id` missing, empty, or over 64 characters. |
| 4403 | `ORIGIN_NOT_ALLOWED` | Origin check failed. |
| 4408 | `START_TIMEOUT` | No `start` within `VOICE_START_TIMEOUT_SECONDS`. |
| 4429 | `DEVICE_DAILY_LIMIT`, `GLOBAL_DAILY_LIMIT`, `CONCURRENT_LIMIT`, `AUDIO_QUOTA_EXCEEDED` | A cap was hit. |
| 4503 | `VOICE_DISABLED` | `VOICE_ENABLED` is false. |

Ordering guarantee: `ready` is always the first server text frame. `ended` or `error` is always the last.

### `GET /api/v1/voice/status`

Headers: `X-Device-ID` required (reuse `get_device_id`). No rate limit (matches the unlimited-GET convention in `backend/app/rate_limit.py`).

Response 200:
```json
{
  "enabled": true,
  "max_duration_s": 180,
  "sessions_per_device_per_day": 2,
  "remaining_today": 2,
  "model": "gemini-3.1-flash-live-preview"
}
```
`remaining_today` is `sessions_per_device_per_day` minus sessions this device started this UTC day, floored at 0. When `enabled` is false, the other fields still carry the configured values and `remaining_today` is 0.

Response 400: existing `get_device_id` error body when the header is missing.

### Live session configuration (what the relay sends to google-genai)

```python
client = genai.Client(api_key=settings.gemini_live_api_key)   # Developer API backend
config = {
    "response_modalities": ["AUDIO"],
    "system_instruction": rendered voice_coach_template.txt,
    "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": voice}}},
    "input_audio_transcription": {},
    "output_audio_transcription": {},
    "realtime_input_config": {"automatic_activity_detection": {"disabled": True}},
}
async with client.aio.live.connect(model=settings.gemini_live_model, config=config) as session: ...
```
No `tools` in this phase. No `context_window_compression`. No `session_resumption`.

### Config (`backend/app/config.py`, `Settings`)

| Field | Env var | Type | Default | Notes |
|---|---|---|---|---|
| `voice_enabled` | `VOICE_ENABLED` | bool | `False` | Feature flag. |
| `gemini_live_api_key` | `GEMINI_LIVE_API_KEY` | str | `""` | Required when `voice_enabled` is true; add to `validate_required_fields` (`config.py:52`). Never logged. |
| `gemini_live_model` | `GEMINI_LIVE_MODEL` | str | `"gemini-3.1-flash-live-preview"` | |
| `voice_coach_voice` | `VOICE_COACH_VOICE` | str | `"Kore"` | |
| `voice_allowed_voices` | `VOICE_ALLOWED_VOICES` | list[str] | `["Kore","Puck","Charon","Aoede","Fenrir","Leda","Orus","Zephyr"]` | Same JSON-or-comma parsing as `allowed_origins` (`config.py:45-50`). |
| `voice_session_max_seconds` | `VOICE_SESSION_MAX_SECONDS` | int | `180` | |
| `voice_sessions_per_device_per_day` | `VOICE_SESSIONS_PER_DEVICE_PER_DAY` | int | `2` | UTC day. |
| `voice_sessions_per_day_global` | `VOICE_SESSIONS_PER_DAY_GLOBAL` | int | `20` | UTC day. |
| `voice_max_concurrent_sessions` | `VOICE_MAX_CONCURRENT_SESSIONS` | int | `2` | |
| `voice_idle_timeout_seconds` | `VOICE_IDLE_TIMEOUT_SECONDS` | int | `45` | Seconds with no client frame of any kind. |
| `voice_start_timeout_seconds` | `VOICE_START_TIMEOUT_SECONDS` | int | `5` | |
| `voice_max_guide_bytes` | `VOICE_MAX_GUIDE_BYTES` | int | `32768` | UTF-8 length of the serialized `study_guide`. |
| `voice_audio_in_price_per_m` | `VOICE_AUDIO_IN_PRICE_PER_M` | float | `3.0` | USD, for the log line only. |
| `voice_audio_out_price_per_m` | `VOICE_AUDIO_OUT_PRICE_PER_M` | float | `12.0` | USD, for the log line only. |

Inbound audio byte quota per session is derived, not configured: `16000 * 2 * voice_session_max_seconds` bytes.

Cap constants for documentation live next to the existing ones in `backend/app/rate_limit.py:55-58` as a comment block referencing the `VOICE_*` settings, so the "keep docs in sync" rule at `rate_limit.py:53-54` still has one place to point at.

### Session end log line (stdout, one JSON object)

```json
{"event":"voice_session_end","session_id":"vs_1a2b3c4d","device_id":"<id>","reason":"max_duration","duration_s":180.2,"audio_in_bytes":1234567,"audio_out_bytes":2345678,"dropped_audio_frames":0,"input_tokens":4500,"output_tokens":9000,"estimated_cost_usd":0.1215,"model":"gemini-3.1-flash-live-preview"}
```
`input_tokens` and `output_tokens` come from the last `usage_metadata` seen on the Live stream when present, otherwise `null`; `estimated_cost_usd` then falls back to `audio_seconds * 25 tokens` per direction times the configured prices.

### Prompt file `backend/app/prompts/voice_coach_template.txt`

Placeholders: `{guide_title}`, `{guide_summary}`, `{guide_sections}` (rendered as `## heading`, content, then `- term: definition` lines per key term). Behavior the prompt must state: speak as a friendly coach; ask one question at a time drawn only from the guide; wait for the student's answer; give brief feedback; keep each coach turn under about 25 seconds of speech; never read the whole guide aloud. Phase 3 replaces this file with the scoring variant.

Internal design is implementer's choice provided these contracts hold. In particular: task structure inside the relay, whether the guard uses a class or module functions, and how the day boundary is computed are free choices.

## Technical Notes

**Non-discoverable context**
- The Live model is reached through the Gemini Developer API with an API key, not through Vertex AI. This is a deliberate user decision (see overview). `google-genai` is a new dependency here; the rest of the backend keeps using `vertexai` (`backend/app/services/gemini_client.py:10-12`). Do not migrate existing code.
- The API key is provisioned as Secret Manager secret `study-buddy-gemini-live-api-key` in project `jking-ai-labs` and injected with `--set-secrets "GEMINI_LIVE_API_KEY=study-buddy-gemini-live-api-key:latest"`. The Cloud Run service account needs `roles/secretmanager.secretAccessor` on that secret.
- `uvicorn` WebSocket support needs the `websockets` package. It is not in `backend/requirements.txt` today.
- The counters are in-process and correct only under `--max-instances=1`. State this in the docs next to the existing rationale (`docs/production-deployment.md:52`).
- Cloud Run request timeout must exceed the session cap. Set `--timeout 300` explicitly in the deploy command (today it is only a troubleshooting note at `docs/production-deployment.md:160`).
- The Live API's own audio-only limit is 15 minutes; ours is 3, so no compression config is needed.

**Integration points**
- `backend/app/main.py:51-55` — include the new router.
- `backend/app/config.py` — new fields and validator update.
- `backend/app/dependencies.py` — `get_live_client` provider.
- `backend/app/routers/voice.py` (new), `backend/app/services/live_client.py` (new), `backend/app/services/voice_session.py` (new), `backend/app/prompts/voice_coach_template.txt` (new).
- `backend/requirements.txt` — add `google-genai>=1.0` and `websockets>=13.0`.
- `backend/.env.example`, `AGENTS.md` (env vars 33-36, security posture table 46-51, endpoints 104-112), `docs/api-contracts.md`, `docs/production-deployment.md` (deploy command, secret, rate table 44-49, timeout), `docs/architecture.md` (new sequence diagram, tech stack row for google-genai).

**Patterns to follow**
- Dependency injection and test override: `backend/app/dependencies.py` `get_gemini_client`, and `backend/tests/conftest.py` `_StickyOverrides` (lines 22-51) plus the autouse cache-clearing fixture (54-72). Add the new guard's `reset()` to that fixture.
- Error envelope shape: `rate_limit_exceeded_handler` in `backend/app/rate_limit.py:70` (`{"code","message"}` under `detail`) — mirror the field names inside the WebSocket `error` frame.
- Settings parsing: `allowed_origins` validator at `backend/app/config.py:45-50`.
- Blocking-call discipline: the Live client is async natively; do not wrap it in `asyncio.to_thread` the way `gemini_client.py:112` does for the sync SDK.

## Acceptance Criteria

- [ ] (R1, R3) `backend/tests/test_voice.py::test_start_then_ready` — `websocket_connect("/api/v1/voice/session")`, send a valid `start`, receive `ready` with `session_id` matching `^vs_[0-9a-f]{8}$` and `max_duration_s == 180`.
- [ ] (R3) `test_audio_relayed_both_directions` — with a fake `LiveClient` that echoes one 480-byte chunk, a client binary frame inside a speech window results in exactly one server binary frame, and fake transcription events arrive as `transcript` frames with roles `user` and `coach`.
- [ ] (R3) `test_audio_outside_speech_window_is_dropped` — a binary frame before `speech_start` is not forwarded and the fake client records zero audio inputs.
- [ ] (R3) `test_bad_first_message_closes_4400` and `test_start_timeout_closes_4408` (use a `VOICE_START_TIMEOUT_SECONDS=0.1` override).
- [ ] (R5) `test_device_daily_cap_closes_4429` — third session for one device in a day closes with 4429 and error code `DEVICE_DAILY_LIMIT`.
- [ ] (R5) `test_global_daily_cap_closes_4429` — with `VOICE_SESSIONS_PER_DAY_GLOBAL=1`, second session from a different device closes 4429 `GLOBAL_DAILY_LIMIT`.
- [ ] (R5) `test_concurrent_cap_closes_4429` — with `VOICE_MAX_CONCURRENT_SESSIONS=1`, a second simultaneous session closes 4429 `CONCURRENT_LIMIT`.
- [ ] (R5) `test_max_duration_ends_session` — with `VOICE_SESSION_MAX_SECONDS=1`, the server sends `ended` with reason `max_duration` and closes 1000 within 3 seconds.
- [ ] (R5) `test_audio_quota_closes_4429` — with `VOICE_SESSION_MAX_SECONDS=1`, sending 40000 bytes of audio closes 4429 `AUDIO_QUOTA_EXCEEDED`.
- [ ] (R5) `test_guide_too_large_closes_4400` — a `start` whose `study_guide` serializes over 32768 bytes closes 4400 `GUIDE_TOO_LARGE`.
- [ ] (R6) `test_origin_not_allowed_closes_4403` — with `ALLOWED_ORIGINS=["https://a.example"]` and `Origin: https://evil.example`, close 4403.
- [ ] (R8) `test_voice_disabled_closes_4503` and `test_status_reports_disabled`.
- [ ] (R2) `test_status_remaining_decrements` — `remaining_today` is 2, then 1 after one session ends.
- [ ] (R7) `test_session_end_log_line` — captured stdout contains one JSON line with `"event": "voice_session_end"` and all fields listed in Contracts.
- [ ] (R9) `grep -n "get_live_client" backend/app/dependencies.py backend/app/routers/voice.py` returns a hit in both files.
- [ ] `cd backend && pytest` passes with no skipped tests.
- [ ] `docs/api-contracts.md` gains a "Voice" section containing every message shape and close code from this spec; `AGENTS.md` security-posture table lists the voice caps; `backend/.env.example` lists every new env var; `docs/production-deployment.md` deploy command includes `--timeout 300` and the `--set-secrets` flag.

## Verification

1. `cd backend && pytest -q` → all tests pass, including the 15 named above.
2. `cd backend && VOICE_ENABLED=true GEMINI_LIVE_API_KEY=<key> GCP_PROJECT_ID=jking-ai-labs FIREBASE_STORAGE_BUCKET=x uvicorn app.main:app --port 8000`, then run `backend/scripts/voice_smoke.py` (new, added in this phase): it connects, sends `start` with `backend/tests/fixtures/sample_study_guide.json`, sends 2 seconds of PCM from `backend/tests/fixtures/hello_16k.pcm` inside a speech window, and prints every text frame. Expected observation: `ready`, at least one `transcript` with role `coach`, at least one binary frame, `turn_complete`, then `ended` with `client_end` after the script sends `end`.
3. `curl -H "X-Device-ID: dev1" localhost:8000/api/v1/voice/status` → 200 with `"enabled": true` and `"remaining_today": 2`.

## Do NOT

- Do not add tools, function calling, or scoring logic (Phase 3).
- Do not touch `frontend/` (Phase 2).
- Do not migrate `gemini_client.py` or any existing service to `google-genai`.
- Do not add `session_resumption`, `context_window_compression`, or reconnect logic.
- Do not persist sessions or counters to Firestore or any external store.
- Do not add dependencies beyond `google-genai` and `websockets`.
- Do not change existing rate-limit constants, CORS settings, or the `X-Device-ID` header contract on existing routes.

## Dependencies

**Requires:** None.
**Blocks:** Phase 2 (consumes this protocol), Phase 3.

## Out of Scope

- Frontend of any kind.
- Vertex AI backend for the Live model (config allows it later by swapping `LiveClient` construction).
- Per-IP limits on the WebSocket (device-keyed caps are the chosen posture).
- Multi-instance safe counters.
