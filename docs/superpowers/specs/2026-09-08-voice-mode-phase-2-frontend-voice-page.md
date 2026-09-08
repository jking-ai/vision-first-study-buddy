# Voice Mode Phase 2: Frontend Voice Page — Design Spec

**Date:** 2026-09-08
**Phase:** 4.2 — Voice Coach frontend
**Part of:** [Voice Mode overview](2026-09-08-voice-mode-overview.md)

---

## What This Phase Delivers

A `/voice` page where the student picks a saved study guide, holds a button to talk, hears the coach, and reads a live transcript, with a countdown and remaining-sessions indicator driven by the Phase 1 backend.

**Why:** Phase 1 is unreachable without a browser client that produces 16 kHz PCM and plays 24 kHz PCM.

## Architecture

```
StudyGuidePage ──"Quiz me by voice"──► navigate("/voice", { state: { studyGuide } })
                                            │
VoicePage ──► useVoiceSession(studyGuide)
               ├─ GET /api/v1/voice/status (X-Device-ID) → remaining, caps
               ├─ WebSocket /api/v1/voice/session → start / speech_start / audio / speech_end / end
               ├─ MicRecorder: getUserMedia → AudioWorklet (pcm-recorder) → Int16 16 kHz frames
               └─ PcmPlayer: AudioContext(24000) → scheduled buffer queue; cleared on "interrupted"
```

## Requirements

1. New route `/voice` rendering `VoicePage`, registered in `frontend/src/App.jsx:33-38`, and a nav item `{ label: "Voice Coach", path: "/voice" }` appended to `NAV_ITEMS` in `frontend/src/components/TopNav.jsx:20-25`.
2. Guide selection: if `location.state?.studyGuide` is present, use it. Otherwise render a select listing `getSavedStudyGuides()` from `frontend/src/utils/studyGuideStorage.js:13`. With no saved guides, render the Empty state.
3. `StudyGuidePage` gets a button labeled `Quiz me by voice` next to the existing save/print actions that navigates to `/voice` with the current guide in router state (same mechanism as `MaterialsPage.jsx:42,46`).
4. A hook `useVoiceSession` in `frontend/src/hooks/useVoiceSession.js` owning the WebSocket, the state machine, the transcript list, and the countdown. States: `idle`, `checking`, `connecting`, `ready`, `talking`, `ended`, `error`.
5. Push-to-talk: a large button labeled `Hold to talk`. `pointerdown` sends `speech_start` and begins streaming; `pointerup`, `pointercancel`, and `pointerleave` send `speech_end` and stop streaming. While the pointer is down, the Space key is not required; on desktop, holding Space performs the same as pointer down while the page has focus.
6. Microphone capture produces raw PCM16 little-endian mono at 16 kHz regardless of the device's native sample rate, sent as binary frames of exactly 4096 samples (8192 bytes) except the final partial frame of a speech window.
7. Playback plays every server binary frame in arrival order as PCM16 mono 24 kHz with no gaps caused by scheduling. On an `interrupted` frame the queue is cleared and playback stops immediately.
8. Transcript panel: append each `transcript` frame as a line prefixed by the role (`You` / `Coach`). Consecutive frames with the same role are concatenated into one line until a `turn_complete` arrives.
9. Countdown from `max_duration_s` in the `ready` frame, shown as `m:ss`. At `0:00` the UI shows the Ended state even if the server frame is late.
10. `End session` button sends `{"type":"end"}`.
11. Status strip reads `GET /api/v1/voice/status` on page load and after every session end: shows `Voice sessions left today: N`. When `enabled` is false or `remaining_today` is 0, the talk button is disabled and the strip explains why.
12. Every close code from Phase 1 maps to a user-facing message (table in Contracts).
13. Vite dev proxy forwards WebSockets: add `ws: true` to the `/api` proxy entry in `frontend/vite.config.js:9-14`.
14. Vitest is configured to run (`test` block with `environment: "jsdom"` in `vite.config.js`) and the tests named in Acceptance Criteria exist and pass.

**Permissions:** Browser microphone permission. Denied permission renders the Error state with the `MIC_DENIED` message.

**Error behavior:** Any WebSocket error or close code other than 1000 moves the hook to `error` with the mapped message and a `Try again` button that re-runs the status check. Audio worklet load failure shows `AUDIO_UNSUPPORTED`. The page never auto-reconnects.

## Contracts

### WebSocket URL

```js
const httpBase = import.meta.env.VITE_API_URL || window.location.origin;
const WS_URL = httpBase.replace(/^http/, "ws") + "/api/v1/voice/session";
```
`API_BASE_URL` semantics are in `frontend/src/api/client.js:10-11`; reuse the same env var, do not add a second one.

### `apiClient.getVoiceStatus()`

Add to the `apiClient` object in `frontend/src/api/client.js:52-100`: `GET /api/v1/voice/status` through the existing `request()` helper so `X-Device-ID` is injected (`client.js:24`).

### Hook API

```js
const {
  state,            // "idle"|"checking"|"connecting"|"ready"|"talking"|"ended"|"error"
  status,           // { enabled, max_duration_s, sessions_per_device_per_day, remaining_today, model } | null
  transcript,       // [{ role: "user"|"coach", text: string }]
  secondsLeft,      // number | null
  error,            // { code: string, message: string } | null
  endedReason,      // string | null
  start,            // () => Promise<void>   opens WS, sends "start"
  pressTalk,        // () => void            speech_start + begin capture
  releaseTalk,      // () => void            speech_end + stop capture
  end,              // () => void            sends {"type":"end"}
  refreshStatus,    // () => Promise<void>
} = useVoiceSession({ studyGuide, voice });
```

### PCM utilities `frontend/src/utils/pcm.js`

- `downsampleTo16k(float32Array, inputSampleRate) → Float32Array` — linear decimation by averaging; when `inputSampleRate === 16000` returns the input unchanged.
- `floatTo16BitPCM(float32Array) → ArrayBuffer` — clamps to [-1, 1], scales to Int16 little-endian.
- `int16ToFloat32(arrayBuffer) → Float32Array` — inverse for playback.

### Worklet `frontend/public/worklets/pcm-recorder.worklet.js`

Registered as `pcm-recorder`. Posts `Float32Array` blocks of the context's native block size to the main thread; the main thread downsamples, converts, and batches into 4096-sample frames. Playback does not use a worklet: it schedules `AudioBuffer`s on an `AudioContext({ sampleRate: 24000 })` at a running `nextStartTime`.

### Close code → message table

| Code / error code | Message shown |
|---|---|
| 4429 `DEVICE_DAILY_LIMIT` | You've used today's voice sessions on this device. Come back tomorrow. |
| 4429 `GLOBAL_DAILY_LIMIT` | The voice coach is fully booked today. Try again tomorrow. |
| 4429 `CONCURRENT_LIMIT` | The coach is busy with other students right now. Try again in a few minutes. |
| 4429 `AUDIO_QUOTA_EXCEEDED` | This session sent more audio than allowed and was ended. |
| 4503 `VOICE_DISABLED` | Voice mode is turned off right now. |
| 4408 `START_TIMEOUT` | The connection timed out before the session started. |
| 4400 any, 4401, 4403 | Something went wrong starting the session. |
| 1011 `UPSTREAM_ERROR` | The voice service hit an error. Please try again. |
| local `MIC_DENIED` | Microphone access is needed for voice mode. Allow it in your browser settings. |
| local `AUDIO_UNSUPPORTED` | Your browser doesn't support the audio features voice mode needs. |

### UI/UX

- **Location:** `/voice`, `frontend/src/pages/VoicePage.jsx`, with components `frontend/src/components/VoiceControls.jsx` (talk button, end button, countdown) and `frontend/src/components/VoiceTranscript.jsx`.
- **Pattern:** Page scaffolding and theming follow `frontend/src/pages/QuizPage.jsx` and `frontend/src/theme.js` (`createAppTheme`). Media permission and cleanup follow `frontend/src/components/CameraCapture.jsx:28-41` (`stopStream` and unmount effect); apply the same to the mic `MediaStream` and both `AudioContext`s.
- **States:**
  - Loading (`checking`): MUI `CircularProgress` with text `Checking voice availability…`.
  - Empty: `Generate a study guide first, then come back to quiz by voice.` with a button to `/study-guide`.
  - Ready (`ready`): guide title, `Start session` button (this is the user gesture that creates the `AudioContext`s; required by iOS Safari).
  - Active (`ready` after `ready` frame, and `talking`): countdown, talk button, transcript, `End session`.
  - Ended: transcript stays visible, `endedReason` mapped to `Session complete` (client_end), `Time's up` (max_duration), `Session ended after inactivity` (idle_timeout), `The coach disconnected` (upstream_closed); `Start another session` button when `remaining_today > 0`.
  - Error: message from the table plus `Try again`.

Internal design is implementer's choice provided these contracts hold.

## Technical Notes

**Non-discoverable context**
- iOS Safari ignores the `sampleRate` hint on `getUserMedia` and often runs the capture context at 48 kHz; the downsampler is mandatory, not defensive.
- `AudioContext` creation must happen inside the `Start session` click handler, or iOS keeps it suspended.
- `pointerleave` must release the talk button; otherwise a finger sliding off the button leaves the mic streaming and the server bills the audio.
- The transcript concatenation rule (R8) exists because the Live API emits transcription in small chunks.
- Firebase Hosting serves the SPA; production WebSocket traffic goes straight to the Cloud Run URL in `VITE_API_URL`, not through Hosting.

**Integration points**
- `frontend/src/App.jsx`, `frontend/src/components/TopNav.jsx`, `frontend/src/pages/StudyGuidePage.jsx`, `frontend/src/api/client.js`, `frontend/vite.config.js`, `frontend/package.json` (add `jsdom` and `@testing-library/react` are already present per `package.json:13-28`; add `jsdom` only if missing).
- New: `pages/VoicePage.jsx`, `components/VoiceControls.jsx`, `components/VoiceTranscript.jsx`, `hooks/useVoiceSession.js`, `utils/pcm.js`, `utils/voiceProtocol.js` (pure reducer over server frames), `public/worklets/pcm-recorder.worklet.js`.
- Docs: `AGENTS.md` frontend inventory (69-72), `docs/architecture.md` source tree, `docs/local-dev-guide.md` (proxy note), `HomePage.jsx:17-36` `steps` array gets a fourth card `Quiz by voice`.

**Patterns to follow**
- Hook shape: `frontend/src/hooks/useQuiz.js` (state, error, async action functions).
- Router state hand-off: `MaterialsPage.jsx:42,46` and `QuizPage.jsx:42`.

## Acceptance Criteria

- [ ] (R6) `frontend/src/utils/pcm.test.js::downsamples 48k to 16k` — 4800 input samples at 48000 produce 1600 output samples; `floatTo16BitPCM` maps 1.0 to 32767 and -1.0 to -32768; a round trip through `int16ToFloat32` is within 1/32768.
- [ ] (R8, R12) `frontend/src/utils/voiceProtocol.test.js` — reducer tests: `ready` sets `secondsLeft`; two consecutive `coach` transcripts merge into one line; `turn_complete` then a new `coach` transcript starts a new line; `interrupted` sets a `clearPlayback` flag; a close with code 4429 and error code `DEVICE_DAILY_LIMIT` yields the exact message from the table.
- [ ] (R1) `grep -n '"/voice"' frontend/src/App.jsx frontend/src/components/TopNav.jsx` returns one hit in each file.
- [ ] (R3) `grep -n "Quiz me by voice" frontend/src/pages/StudyGuidePage.jsx` returns a hit.
- [ ] (R13) `grep -n "ws: true" frontend/vite.config.js` returns a hit.
- [ ] (R14) `cd frontend && npm test` runs Vitest and exits 0 with at least the two test files above.
- [ ] `cd frontend && npm run build` exits 0.
- [ ] `cd backend && pytest` still passes (no backend change expected; confirms nothing regressed).
- [ ] `AGENTS.md`, `docs/architecture.md`, `docs/local-dev-guide.md` updated per Integration points.

## Verification

1. `cd frontend && npm test` and `npm run build` → both exit 0.
2. Manual, against a Phase 1 backend with `VOICE_ENABLED=true`: `bash scripts/dev.sh`, open `http://localhost:5173/voice` in Chrome, select a saved guide, click `Start session`, hold the button and say "I'm ready", release. Expected observation: transcript shows a `You` line with the words, then a `Coach` line, and coach audio plays; the countdown decrements from `3:00`; clicking `End session` shows `Session complete`; the status strip drops from 2 to 1.
3. Manual on iOS Safari (any iPhone): same flow. Expected observation: audio plays after `Start session`, and releasing the button by sliding off it stops the transcript from growing.

## Do NOT

- Do not add camera or video streaming.
- Do not implement server VAD, open-mic mode, or barge-in UI beyond honoring `interrupted`.
- Do not add global state libraries; keep `useState` plus hooks per house pattern.
- Do not modify backend code in this phase.
- Do not add new env vars; `VITE_API_URL` covers the WebSocket base.
- Do not add dependencies other than `jsdom` (if absent) for Vitest.

## Dependencies

**Requires:** Phase 1 (the WebSocket protocol and status endpoint this page consumes).
**Blocks:** Phase 3.

## Out of Scope

- Scoring, answer recording, quiz history (Phase 3).
- Voice selection UI (hook accepts `voice`, page passes `undefined` in this phase).
- Session resumption after a dropped connection.
