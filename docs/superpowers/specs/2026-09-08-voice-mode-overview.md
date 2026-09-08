# Voice Mode — Feature Overview

**Date:** 2026-09-08
**Phase:** 4 — Voice Coach (new)
**Phase specs:** [Phase 1](2026-09-08-voice-mode-phase-1-backend-relay.md) · [Phase 2](2026-09-08-voice-mode-phase-2-frontend-voice-page.md) · [Phase 3](2026-09-08-voice-mode-phase-3-oral-quiz-scoring.md)

---

## Feature

A push-to-talk voice coach that quizzes the student out loud over a study guide they already generated. The browser streams microphone audio to a WebSocket relay on the existing Cloud Run backend. The relay holds the Gemini Live API session, forwards audio both ways, and enforces hard spend caps. In the final phase the coach records each answer through function calls and the result lands in the existing quiz history.

## Decisions made during spec'ing (not discoverable from the repo)

| Decision | Choice | Why |
|---|---|---|
| Live model | `gemini-3.1-flash-live-preview` via the Gemini Developer API (AI Studio), API key in Secret Manager | The 3.1 Live model is not on Vertex AI as of 2026-09-08. User accepted the off-Vertex trade for audio quality. Model and backend are config values so a Vertex switch later is a redeploy, not a code change. |
| Turn-taking | Push-to-talk (manual activity signals, server VAD disabled) | Predictable spend, no silence billed, simpler on mobile Safari. |
| Spend posture | 3 min per session, 2 sessions per device per day, 20 sessions per day globally, 2 concurrent | Demo posture. Worst case about $0.07 per session at $3/M audio in and $12/M audio out (25 tokens per audio second). |
| Study guide source | Client sends the full `StudyGuide` JSON in the `start` message | Server-side `_study_guides` dict (`backend/app/routers/study_guides.py:15`) is in-process, lost on redeploy, and has no device check. Saved guides already live client-side in localStorage (`frontend/src/utils/studyGuideStorage.js`). |
| Camera during voice | Out of scope | Audio plus video sessions cap at 2 minutes without context compression; not worth it for a 3-minute demo. |
| Browser to Live API connection | Relay through Cloud Run, never direct with ephemeral tokens | Caps must be enforced server-side; a direct connection would bypass them. |
| Rate-limit storage | In-process counters, same as `slowapi` today | Depends on `--max-instances=1`, already the documented posture (`docs/production-deployment.md:52`). |

## Phase breakdown

| Phase | Delivers | Requires |
|---|---|---|
| 1 — Backend relay | `WS /api/v1/voice/session`, `GET /api/v1/voice/status`, caps, transcripts, deploy config | None |
| 2 — Frontend voice page | `/voice` route, mic capture, playback, transcript, timer, guide picker | Phase 1 (consumes the WebSocket protocol) |
| 3 — Oral quiz scoring | `record_answer` / `end_quiz` tool calls, score panel, quiz history entry | Phase 1 and Phase 2 (extends protocol and page) |

## Dependency graph

```
Phase 1 ──► Phase 2 ──► Phase 3
```

## External facts the implementer should re-verify before starting

- Live API audio formats: input raw 16-bit PCM, 16 kHz, mono, little-endian; output raw 16-bit PCM, 24 kHz. Source: https://ai.google.dev/gemini-api/docs/live-api
- Audio-only sessions without context compression are limited to 15 minutes. Our cap is 3 minutes, so compression is not configured. Source: https://ai.google.dev/gemini-api/docs/live-api/session-management
- Manual activity signals: `realtime_input_config.automatic_activity_detection.disabled = True`, then `session.send_realtime_input(activity_start=types.ActivityStart())` and `activity_end=types.ActivityEnd()`. Source: https://ai.google.dev/gemini-api/docs/live-api/capabilities
- Cloud Run supports WebSockets with no configuration; connection life is bounded by the service request timeout. Source: https://docs.cloud.google.com/run/docs/triggering/websockets
- Live API pricing used for the cost log line: $3.00 per 1M audio input tokens, $12.00 per 1M audio output tokens, 25 tokens per audio second. Re-check https://ai.google.dev/gemini-api/docs/pricing and set the config values accordingly.
