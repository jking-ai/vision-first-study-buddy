# Quiz Generation & Grading Pipeline — Design Spec

**Date:** 2026-03-15
**Issue:** jking-ai/vision-first-study-buddy#6
**Phase:** 2 — Core Features

---

## Problem

Students upload study materials (photos, PDFs, epubs) to Vision-First Study Buddy. Phase 2 delivers end-to-end quiz generation and grading: generate quizzes from uploaded materials via Gemini, then grade submitted answers using exact match (MC/TF) and semantic comparison (short answer).

---

## Architecture

```
POST /api/v1/quizzes/generate
  → QuizGenerator.generate()
      → StorageClient.get_material_blobs()    # get blob list per material_id
      → StorageClient.get_file_bytes()         # download raw bytes
      → MaterialProcessor.prepare_for_gemini() # convert to Gemini content parts
      → QuizGenerator._build_prompt()          # interpolate quiz_template.txt
      → GeminiClient.generate_multimodal()     # Vertex AI call → structured JSON
      → parse into Quiz Pydantic model
      → store QuizResponse in _quizzes dict
  ← QuizResponse (201)

GET /api/v1/quizzes/{id}
  → lookup _quizzes[id]
  ← QuizResponse (200) or 404

POST /api/v1/quizzes/{id}/submit
  → validate answers reference real question IDs
  → QuizGenerator.grade_submission()
      → MC/TF: exact string match (case-insensitive)
      → short_answer: GeminiClient.grade_short_answer() → is_correct + explanation
      → aggregate QuizScore
  ← QuizSubmissionResponse (200)
```

---

## Components

### GeminiClient (app/services/gemini_client.py)

Wraps Vertex AI SDK. Initialized once with `vertexai.init()` in `__init__`. Creates a new `GenerativeModel` per call (to pass `system_instruction`). Uses `asyncio.to_thread()` for blocking SDK calls.

- `generate_multimodal(content_parts, system_instruction)` — assembles `Part` objects from inline_data/text dicts, calls Gemini with `response_mime_type="application/json"`, returns parsed JSON dict.
- `grade_short_answer(student_answer, correct_answer)` — sends a comparison prompt, returns `{"is_correct": bool, "explanation": str}`.
- `_build_parts(content_parts)` — converts `{"inline_data": {...}}` and `{"text": ...}` dicts into `vertexai.generative_models.Part` objects.

### QuizGenerator (app/services/quiz_generator.py)

Dependencies: `GeminiClient`, `StorageClient`, `MaterialProcessor`.

- `generate(material_ids, num_questions, difficulty, question_types)` → `QuizResponse`
  - Fetches blobs, downloads bytes, prepares content parts
  - Interpolates `quiz_template.txt` with difficulty instruction and question types
  - Calls Gemini, parses JSON into `Quiz` model with `qz_{8-char-hex}` ID
- `grade_submission(quiz: Quiz, answers: list[dict])` → `QuizSubmissionResponse`
  - MC/TF: case-insensitive exact match against `correct_answer`
  - short_answer: calls `GeminiClient.grade_short_answer()`
- `_build_prompt(num_questions, difficulty, question_types)` — interpolates template
- `_fetch_material_parts(material_ids)` — downloads all blobs and prepares content parts; raises `ValueError` if any material_id has no blobs

### Quizzes Router (app/routers/quizzes.py)

Module-level `_quizzes: dict[str, QuizResponse]` for in-memory storage.

Dependencies injected via FastAPI `Depends()`.

Error mapping:
- `ValueError` → 400 `VALIDATION_ERROR`
- `GenerationError` (503 substring) → 503 `MODEL_UNAVAILABLE`
- `GenerationError` → 500 `GENERATION_FAILED`
- Missing quiz ID → 404 `QUIZ_NOT_FOUND`
- Invalid question IDs in submission → 400 `VALIDATION_ERROR`

### Dependencies (app/dependencies.py)

Two new factories:
- `get_gemini_client(settings)` → `GeminiClient`
- `get_quiz_generator(gemini_client, storage_client, material_processor)` → `QuizGenerator`

---

## Prompt Design

`quiz_template.txt` uses three interpolation variables:
- `{num_questions}` — integer
- `{difficulty_instruction}` — one of four sentences mapping easy/medium/hard/mixed to Bloom's-aligned descriptions
- `{question_types}` — comma-separated readable names (e.g., "multiple choice, short answer")

The template already specifies JSON output schema. No strict `response_schema` is passed to Gemini — `response_mime_type="application/json"` is sufficient for well-structured output.

---

## Data Flow: Content Parts

`material_processor.prepare_for_gemini()` returns:
- Images/PDFs: `{"inline_data": {"mime_type": ..., "data": <base64str>}}`
- EPUBs: `{"text": <extracted_text>}`

`GeminiClient._build_parts()` converts these to Vertex AI `Part` objects:
- `Part.from_data(data=decoded_bytes, mime_type=...)` for binary
- `Part.from_text(text)` for text

---

## Error Handling

| Scenario | HTTP | Code |
|---|---|---|
| Empty material_ids or material not in storage | 400 | VALIDATION_ERROR |
| Invalid question_id in submission | 400 | VALIDATION_ERROR |
| Quiz ID not found | 404 | QUIZ_NOT_FOUND |
| Gemini call fails | 500 | GENERATION_FAILED |
| Gemini unavailable (503) | 503 | MODEL_UNAVAILABLE |

---

## Testing Strategy

All external dependencies (GeminiClient, StorageClient, MaterialProcessor) are mocked via `AsyncMock` and `app.dependency_overrides`. Tests cover:
- Happy path: generate quiz, retrieve quiz, submit answers
- Error paths: missing materials, invalid question IDs, Gemini failure, quiz not found
- Grading logic: MC exact match, TF exact match, short answer via Gemini
