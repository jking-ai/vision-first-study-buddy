# Voice Mode Phase 3: Oral Quiz Scoring — Design Spec

**Date:** 2026-09-08
**Phase:** 4.3 — Voice Coach scoring
**Part of:** [Voice Mode overview](2026-09-08-voice-mode-overview.md)

---

## What This Phase Delivers

The coach runs a fixed-length oral quiz, records each answer through a function call, and ends with a summary. The frontend shows a running score and stores the result in the existing quiz history.

**Why:** Turns a conversation into a measurable study activity and connects voice mode to the quiz history the app already keeps.

## Architecture

```
Live session (tools: record_answer, end_quiz)
   │ tool_call record_answer → relay appends to session.results
   │                         → client {"type":"answer_recorded", ...}
   │                         → send_tool_response({"status":"ok","recorded":n})
   │ tool_call end_quiz     → client {"type":"quiz_summary", ...}
   │                         → send_tool_response({"status":"ok"})
   │                         → after the coach's closing turn completes: ended(reason="quiz_complete"), close 1000
VoicePage ── on quiz_summary ──► saveQuizResult({..., mode:"voice"}) (frontend/src/utils/quizHistory.js:27)
```

## Requirements

1. The Live session config gains `tools` with two function declarations (Contracts). No other tools.
2. The relay executes tool calls locally, emits the client frames in Contracts, and replies with `send_tool_response` for every call, including malformed ones.
3. `voice_coach_template.txt` is replaced by a scoring variant that instructs the coach to ask exactly `{num_questions}` questions one at a time, call `record_answer` after each student answer, and call `end_quiz` once after the last question, then say goodbye in one short sentence.
4. New setting `voice_quiz_questions` (`VOICE_QUIZ_QUESTIONS`, int, default `5`, allowed 3..10). The `start` message may override with `"num_questions"` within the same range; out-of-range closes 4400 `INVALID_NUM_QUESTIONS`.
5. After `end_quiz` is received, the relay ends the session with reason `quiz_complete` once the next `turn_complete` arrives, or after 15 seconds, whichever comes first.
6. The session end log line gains `questions_asked` and `questions_correct` integers.
7. Frontend: `VoicePage` shows a score chip `Score: k / n` updated on every `answer_recorded`, a per-answer list (question, your answer, correct or not, feedback), and on `quiz_summary` saves a history entry and shows the summary text.
8. `saveQuizResult` in `frontend/src/utils/quizHistory.js:27` accepts an optional `mode` field, stored as `"voice"` or `"written"` (default `"written"` when absent). `QuizPage`'s history list shows a `Voice` chip for entries with `mode === "voice"`.
9. Guardrail: at most `num_questions` `record_answer` calls are honored per session; further calls get tool response `{"status":"ignored","reason":"quiz_full"}` and no client frame.

**Permissions:** Unchanged from Phase 1.

**Error behavior:** A tool call with missing or wrongly typed arguments receives `{"status":"error","reason":"invalid_arguments"}` as its tool response and emits no client frame; the session continues. If `end_quiz` never arrives, Phase 1's max-duration and idle rules still end the session and the frontend saves nothing to history.

## Contracts

### Function declarations (sent in the Live `tools` config)

```json
{
  "name": "record_answer",
  "description": "Record the student's answer to the question just asked. Call exactly once per question, right after the student answers.",
  "parameters": {
    "type": "object",
    "properties": {
      "question": {"type": "string", "description": "The question as asked"},
      "student_answer": {"type": "string", "description": "What the student said, paraphrased"},
      "correct": {"type": "boolean"},
      "feedback": {"type": "string", "description": "One sentence of feedback"}
    },
    "required": ["question", "student_answer", "correct", "feedback"]
  }
}
```
```json
{
  "name": "end_quiz",
  "description": "Call once after the final question has been recorded.",
  "parameters": {
    "type": "object",
    "properties": {"summary": {"type": "string", "description": "Two sentences summarizing strengths and what to review"}},
    "required": ["summary"]
  }
}
```

### Tool responses (relay → Live)

- `record_answer` honored: `{"status":"ok","recorded":<count so far>,"remaining":<num_questions - count>}`
- `record_answer` beyond the cap: `{"status":"ignored","reason":"quiz_full"}`
- Invalid arguments: `{"status":"error","reason":"invalid_arguments"}`
- `end_quiz`: `{"status":"ok"}`

### New server → client frames

| Shape | When |
|---|---|
| `{"type":"answer_recorded","index":<1-based int>,"question":"<string>","student_answer":"<string>","correct":<bool>,"feedback":"<string>","score":{"correct":<int>,"total":<int>}}` | Each honored `record_answer`. `total` is `num_questions`. |
| `{"type":"quiz_summary","summary":"<string>","score":{"correct":<int>,"asked":<int>,"total":<int>}}` | `end_quiz` received. |

`ended.reason` gains the value `quiz_complete`.

### `start` message addition

`"num_questions": <int 3..10>` optional.

### Quiz history entry (localStorage `vfsb_quiz_history`)

Existing fields at `quizHistory.js:31-39` plus `mode: "voice"`. For voice entries: `quizId` is the `session_id`, `title` is `Voice: <guide title>`, `score` is `correct`, `total` is `num_questions`, `percentage` is `round(100 * correct / total)`.

### Prompt file `backend/app/prompts/voice_coach_template.txt` (replaced)

Placeholders: Phase 1's plus `{num_questions}`. Required stated behavior: greet in one sentence and ask question 1 immediately; one question per turn; after each answer, give one sentence of feedback and call `record_answer` before asking the next question; never reveal the score mid-quiz; after the final answer call `end_quiz` then say one closing sentence; questions must be answerable from the guide content only.

Internal design is implementer's choice provided these contracts hold.

## Technical Notes

**Non-discoverable context**
- Tool calls arrive on the Live stream as `response.tool_call.function_calls`, each with `id`, `name`, `args`; replies go through `session.send_tool_response(function_responses=[types.FunctionResponse(id=..., name=..., response={...})])`. Source: https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk
- The model may call `record_answer` and continue speaking in the same turn; the relay must not block audio forwarding while handling a tool call.
- The 15-second fallback in R5 exists because the closing turn sometimes never produces `turn_complete` after a tool call.

**Integration points**
- `backend/app/services/voice_session.py` (tool dispatch), `backend/app/services/live_client.py` (tool config passthrough), `backend/app/config.py`, `backend/app/prompts/voice_coach_template.txt`, `backend/tests/test_voice.py`.
- `frontend/src/hooks/useVoiceSession.js`, `frontend/src/utils/voiceProtocol.js`, `frontend/src/pages/VoicePage.jsx`, new `frontend/src/components/VoiceScorePanel.jsx`, `frontend/src/utils/quizHistory.js`, `frontend/src/pages/QuizPage.jsx` (history chip).
- Docs: `docs/api-contracts.md` (new frames, tool declarations), `AGENTS.md` (env var, endpoints), `README.md` success criteria gain item 9: "Voice quiz records a scored result in quiz history".

**Patterns to follow**
- Score display: `QuizView.jsx` result rendering and the MUI `Chip` usage there.
- History persistence: `saveQuizResult` call site in `QuizPage.jsx`.

## Acceptance Criteria

- [ ] (R1) `backend/tests/test_voice.py::test_tools_declared` — the fake `LiveClient` receives a config whose `tools` contain function declarations named exactly `record_answer` and `end_quiz`.
- [ ] (R2, R7) `test_record_answer_emits_frame_and_response` — a fake tool call yields one `answer_recorded` frame with `index == 1` and `score == {"correct": 1, "total": 5}`, and the fake receives a tool response `{"status":"ok","recorded":1,"remaining":4}`.
- [ ] (R9) `test_record_answer_beyond_cap_ignored` — the sixth call gets `{"status":"ignored","reason":"quiz_full"}` and no frame.
- [ ] (R2) `test_invalid_tool_args_error_response` — missing `correct` yields `{"status":"error","reason":"invalid_arguments"}`.
- [ ] (R5) `test_end_quiz_summary_then_quiz_complete` — `end_quiz` yields a `quiz_summary` frame, then after the fake emits `turn_complete`, `ended` with reason `quiz_complete` and close 1000.
- [ ] (R5) `test_end_quiz_fallback_timeout` — with the fallback overridden to 0.2 seconds and no `turn_complete`, `ended` with `quiz_complete` still arrives.
- [ ] (R4) `test_num_questions_out_of_range_closes_4400` — `num_questions: 11` closes 4400 `INVALID_NUM_QUESTIONS`.
- [ ] (R6) `test_session_end_log_line_has_quiz_counts` — log line contains `questions_asked` and `questions_correct`.
- [ ] (R7, R8) `frontend/src/utils/voiceProtocol.test.js` — `answer_recorded` updates score state; `quiz_summary` produces a `saveHistory` payload with `mode: "voice"`, `total: 5`, and `percentage` computed as specified.
- [ ] (R8) `frontend/src/utils/quizHistory.test.js` — `saveQuizResult({...})` without `mode` stores `"written"`; with `mode: "voice"` stores `"voice"`.
- [ ] (R8) `grep -n 'mode === "voice"' frontend/src/pages/QuizPage.jsx` returns a hit.
- [ ] `cd backend && pytest` and `cd frontend && npm test && npm run build` exit 0.
- [ ] `docs/api-contracts.md`, `AGENTS.md`, `README.md` updated per Integration points.

## Verification

1. `cd backend && pytest -q` and `cd frontend && npm test` → exit 0.
2. Manual, full stack with `VOICE_ENABLED=true`: start a session, answer five questions out loud. Expected observation: the score chip increments after each answer, the per-answer list shows five rows, the summary text appears, the session ends on its own, and `/quiz` history shows a new entry with a `Voice` chip and the same score.
3. `backend/scripts/voice_smoke.py --questions 3` (extend the Phase 1 script) → prints three `answer_recorded` frames and one `quiz_summary` when driven by the fixture audio and the real model. Observation may vary with the model's speech; the script must at minimum print `ready` and exit on `ended`.

## Do NOT

- Do not add tools beyond the two declared.
- Do not grade answers server-side with a second Gemini call; the coach's `correct` flag is the score.
- Do not persist voice results server-side.
- Do not change written-quiz grading or `QuizView`.
- Do not alter Phase 1 caps or close codes except adding `INVALID_NUM_QUESTIONS` and the `quiz_complete` reason.

## Dependencies

**Requires:** Phase 1 (relay and tool passthrough point), Phase 2 (page and protocol reducer being extended).
**Blocks:** None.

## Out of Scope

- Adaptive difficulty or follow-up questions.
- Sharing or exporting voice results.
- Camera frames during the quiz.
