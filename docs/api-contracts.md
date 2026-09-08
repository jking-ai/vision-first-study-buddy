# API Contracts -- Vision-First Study Buddy

## Base URL

- **Local development:** `http://localhost:8000`
- **Production:** `https://vision-first-study-buddy-<hash>-uc.a.run.app`

All endpoints are prefixed with `/api/v1`.

---

## Authentication

No authentication is required for the MVP. All endpoints are publicly accessible. Future iterations may add Firebase Authentication for per-user material isolation.

---

## Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check and service metadata |
| `POST` | `/api/v1/materials/upload` | Upload images, PDFs, or epubs |
| `GET` | `/api/v1/materials` | List all uploaded materials |
| `GET` | `/api/v1/materials/{id}` | Get details for a specific material |
| `POST` | `/api/v1/study-guides/generate` | Generate a study guide from selected materials |
| `GET` | `/api/v1/study-guides/{id}` | Retrieve a generated study guide |
| `POST` | `/api/v1/quizzes/generate` | Generate a quiz from selected materials |
| `GET` | `/api/v1/quizzes/{id}` | Retrieve a generated quiz |
| `POST` | `/api/v1/quizzes/{id}/submit` | Submit quiz answers for grading |

---

## Error Response Format

All error responses follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description of what went wrong.",
    "details": []
  }
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Request body or file failed validation |
| 400 | `UNSUPPORTED_FILE_TYPE` | The uploaded file type is not supported |
| 400 | `FILE_TOO_LARGE` | The uploaded file exceeds the size limit |
| 404 | `MATERIAL_NOT_FOUND` | The specified material ID does not exist |
| 404 | `STUDY_GUIDE_NOT_FOUND` | The specified study guide ID does not exist |
| 404 | `QUIZ_NOT_FOUND` | The specified quiz ID does not exist |
| 422 | `UNPROCESSABLE_ENTITY` | FastAPI automatic validation error |
| 500 | `GENERATION_FAILED` | The LLM call failed or returned an unparseable response |
| 500 | `STORAGE_ERROR` | Firebase Storage operation failed |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `MODEL_UNAVAILABLE` | The Gemini model is temporarily unavailable |

---

## Endpoint Details

### GET /api/v1/health

Returns service status and metadata. Used by Cloud Run health checks and frontend connectivity verification.

**Request:** No parameters.

**curl example:**

```bash
curl http://localhost:8000/api/v1/health
```

**Response (200 OK):**

```json
{
  "status": "healthy",
  "service": "vision-first-study-buddy",
  "version": "1.0.0",
  "model": "gemini-3.1-pro-preview",
  "storage_bucket": "my-project.appspot.com"
}
```

---

### POST /api/v1/materials/upload

Upload one or more files (images, PDFs, epubs) to Firebase Storage.

**Request Headers:**
- `Content-Type: multipart/form-data`

**Request Body:** Multipart form with one or more files.

**Supported file types:**
- Images: `image/jpeg`, `image/png`, `image/webp`
- Documents: `application/pdf`
- Ebooks: `application/epub+zip`

**Maximum file size:** 20 MB per file.

**curl example:**

```bash
curl -X POST http://localhost:8000/api/v1/materials/upload \
  -F "files=@lecture-notes-page1.jpg" \
  -F "files=@chapter-5.pdf"
```

**Response (201 Created):**

```json
{
  "materials": [
    {
      "id": "mat_a1b2c3d4",
      "filename": "lecture-notes-page1.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 2048576,
      "storage_url": "gs://my-project.appspot.com/materials/mat_a1b2c3d4/lecture-notes-page1.jpg",
      "uploaded_at": "2026-02-27T10:30:00Z"
    },
    {
      "id": "mat_e5f6g7h8",
      "filename": "chapter-5.pdf",
      "content_type": "application/pdf",
      "size_bytes": 5242880,
      "storage_url": "gs://my-project.appspot.com/materials/mat_e5f6g7h8/chapter-5.pdf",
      "uploaded_at": "2026-02-27T10:30:01Z"
    }
  ]
}
```

**Response (400 Bad Request -- unsupported file type):**

```json
{
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "File type 'application/zip' is not supported. Accepted types: image/jpeg, image/png, image/webp, application/pdf, application/epub+zip.",
    "details": [
      {
        "filename": "archive.zip",
        "content_type": "application/zip"
      }
    ]
  }
}
```

---

### GET /api/v1/materials

List all uploaded materials.

**Request:** No parameters.

**curl example:**

```bash
curl http://localhost:8000/api/v1/materials
```

**Response (200 OK):**

```json
{
  "materials": [
    {
      "id": "mat_a1b2c3d4",
      "filename": "lecture-notes-page1.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 2048576,
      "storage_url": "gs://my-project.appspot.com/materials/mat_a1b2c3d4/lecture-notes-page1.jpg",
      "uploaded_at": "2026-02-27T10:30:00Z"
    },
    {
      "id": "mat_e5f6g7h8",
      "filename": "chapter-5.pdf",
      "content_type": "application/pdf",
      "size_bytes": 5242880,
      "storage_url": "gs://my-project.appspot.com/materials/mat_e5f6g7h8/chapter-5.pdf",
      "uploaded_at": "2026-02-27T10:30:01Z"
    }
  ]
}
```

---

### GET /api/v1/materials/{id}

Get details for a specific uploaded material, including a preview URL.

**Request:** Path parameter `id` (string).

**curl example:**

```bash
curl http://localhost:8000/api/v1/materials/mat_a1b2c3d4
```

**Response (200 OK):**

```json
{
  "id": "mat_a1b2c3d4",
  "filename": "lecture-notes-page1.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 2048576,
  "storage_url": "gs://my-project.appspot.com/materials/mat_a1b2c3d4/lecture-notes-page1.jpg",
  "preview_url": "https://storage.googleapis.com/my-project.appspot.com/materials/mat_a1b2c3d4/lecture-notes-page1.jpg?X-Goog-SignedHeaders=...",
  "uploaded_at": "2026-02-27T10:30:00Z"
}
```

**Response (404 Not Found):**

```json
{
  "error": {
    "code": "MATERIAL_NOT_FOUND",
    "message": "No material found with ID 'mat_invalid'.",
    "details": []
  }
}
```

---

### POST /api/v1/study-guides/generate

Generate a study guide from one or more uploaded materials. The backend fetches the materials from Firebase Storage, sends them as multimodal content to Gemini, and returns a structured study guide.

**Request Headers:**
- `Content-Type: application/json`

**Request Body Schema:**

```json
{
  "material_ids": ["string (required) -- List of material IDs to include"],
  "focus_topics": ["string (optional) -- Specific topics to focus on"],
  "detail_level": "string (optional, default: 'standard') -- One of: brief, standard, detailed"
}
```

**curl example:**

```bash
curl -X POST http://localhost:8000/api/v1/study-guides/generate \
  -H "Content-Type: application/json" \
  -d '{
    "material_ids": ["mat_a1b2c3d4", "mat_e5f6g7h8"],
    "focus_topics": ["cell division", "mitosis vs meiosis"],
    "detail_level": "detailed"
  }'
```

**Response (200 OK):**

```json
{
  "study_guide": {
    "id": "sg_x1y2z3w4",
    "title": "Cell Division: Mitosis and Meiosis",
    "summary": "A comprehensive overview of cell division processes, comparing mitosis and meiosis across key dimensions including stages, chromosome behavior, and biological purpose.",
    "sections": [
      {
        "heading": "Key Concepts",
        "content": "Cell division is the process by which a parent cell divides into two or more daughter cells...",
        "key_terms": [
          {
            "term": "Mitosis",
            "definition": "A type of cell division resulting in two genetically identical daughter cells."
          },
          {
            "term": "Meiosis",
            "definition": "A type of cell division resulting in four genetically diverse gamete cells with half the chromosome number."
          }
        ]
      },
      {
        "heading": "Mitosis Stages",
        "content": "Mitosis occurs in five stages: prophase, prometaphase, metaphase, anaphase, and telophase...",
        "key_terms": []
      },
      {
        "heading": "Comparison: Mitosis vs. Meiosis",
        "content": "While both processes involve cell division, they differ in purpose, outcome, and mechanism...",
        "key_terms": []
      }
    ],
    "source_materials": ["mat_a1b2c3d4", "mat_e5f6g7h8"],
    "generated_at": "2026-02-27T10:35:00Z"
  },
  "metadata": {
    "model": "gemini-3.1-pro-preview",
    "generation_time_ms": 8750,
    "material_count": 2,
    "request_id": "req_p1q2r3s4t5u6"
  }
}
```

**Response (400 Bad Request -- no materials):**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "At least one material_id is required.",
    "details": [
      {
        "field": "material_ids",
        "value": [],
        "reason": "List must contain at least one item."
      }
    ]
  }
}
```

---

### GET /api/v1/study-guides/{id}

Retrieve a previously generated study guide by ID.

**Request:** Path parameter `id` (string).

**curl example:**

```bash
curl http://localhost:8000/api/v1/study-guides/sg_x1y2z3w4
```

**Response (200 OK):** Same structure as the `study_guide` field in the generate response.

**Response (404 Not Found):**

```json
{
  "error": {
    "code": "STUDY_GUIDE_NOT_FOUND",
    "message": "No study guide found with ID 'sg_invalid'.",
    "details": []
  }
}
```

---

### POST /api/v1/quizzes/generate

Generate a quiz from one or more uploaded materials.

**Request Headers:**
- `Content-Type: application/json`

**Request Body Schema:**

```json
{
  "material_ids": ["string (required) -- List of material IDs to include"],
  "num_questions": "integer (optional, default: 10) -- Number of questions to generate (5-25)",
  "difficulty": "string (optional, default: 'mixed') -- One of: easy, medium, hard, mixed",
  "question_types": ["string (optional, default: ['multiple_choice', 'short_answer']) -- Types of questions"]
}
```

**curl example:**

```bash
curl -X POST http://localhost:8000/api/v1/quizzes/generate \
  -H "Content-Type: application/json" \
  -d '{
    "material_ids": ["mat_a1b2c3d4", "mat_e5f6g7h8"],
    "num_questions": 5,
    "difficulty": "mixed",
    "question_types": ["multiple_choice", "short_answer"]
  }'
```

**Response (200 OK):**

```json
{
  "quiz": {
    "id": "qz_m1n2o3p4",
    "title": "Cell Division Quiz",
    "questions": [
      {
        "id": "q1",
        "type": "multiple_choice",
        "difficulty": "easy",
        "question": "What is the primary purpose of mitosis?",
        "options": [
          "A) To produce gametes for sexual reproduction",
          "B) To produce two genetically identical daughter cells",
          "C) To reduce chromosome number by half",
          "D) To generate genetic diversity"
        ],
        "correct_answer": "B",
        "explanation": "Mitosis produces two daughter cells that are genetically identical to the parent cell. This is essential for growth, repair, and asexual reproduction."
      },
      {
        "id": "q2",
        "type": "short_answer",
        "difficulty": "medium",
        "question": "Describe the key difference between prophase I of meiosis and prophase of mitosis.",
        "correct_answer": "In prophase I of meiosis, homologous chromosomes pair up and undergo crossing over (recombination), which does not occur in mitotic prophase.",
        "explanation": "Crossing over during prophase I is a major source of genetic variation in sexually reproducing organisms."
      }
    ],
    "source_materials": ["mat_a1b2c3d4", "mat_e5f6g7h8"],
    "generated_at": "2026-02-27T10:40:00Z"
  },
  "metadata": {
    "model": "gemini-3.1-pro-preview",
    "generation_time_ms": 6200,
    "material_count": 2,
    "request_id": "req_v1w2x3y4z5a6"
  }
}
```

---

### GET /api/v1/quizzes/{id}

Retrieve a previously generated quiz by ID.

**Request:** Path parameter `id` (string).

**curl example:**

```bash
curl http://localhost:8000/api/v1/quizzes/qz_m1n2o3p4
```

**Response (200 OK):** Same structure as the `quiz` field in the generate response.

**Response (404 Not Found):**

```json
{
  "error": {
    "code": "QUIZ_NOT_FOUND",
    "message": "No quiz found with ID 'qz_invalid'.",
    "details": []
  }
}
```

---

### POST /api/v1/quizzes/{id}/submit

Submit answers for a quiz and receive graded results.

**Request Headers:**
- `Content-Type: application/json`

**Request Body Schema:**

```json
{
  "answers": [
    {
      "question_id": "string -- ID of the question being answered",
      "answer": "string -- The student's answer (letter for multiple choice, text for short answer)"
    }
  ]
}
```

**curl example:**

```bash
curl -X POST http://localhost:8000/api/v1/quizzes/qz_m1n2o3p4/submit \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": "q1", "answer": "B"},
      {"question_id": "q2", "answer": "During prophase I, homologous chromosomes pair up and exchange genetic material through crossing over."}
    ]
  }'
```

**Response (200 OK):**

```json
{
  "quiz_id": "qz_m1n2o3p4",
  "score": {
    "correct": 2,
    "total": 2,
    "percentage": 100.0
  },
  "results": [
    {
      "question_id": "q1",
      "submitted_answer": "B",
      "correct_answer": "B",
      "is_correct": true,
      "explanation": "Mitosis produces two daughter cells that are genetically identical to the parent cell."
    },
    {
      "question_id": "q2",
      "submitted_answer": "During prophase I, homologous chromosomes pair up and exchange genetic material through crossing over.",
      "correct_answer": "In prophase I of meiosis, homologous chromosomes pair up and undergo crossing over (recombination), which does not occur in mitotic prophase.",
      "is_correct": true,
      "explanation": "Your answer correctly identifies crossing over as the key difference. Crossing over during prophase I is a major source of genetic variation."
    }
  ],
  "submitted_at": "2026-02-27T10:45:00Z"
}
```

---

## Data Models

### Pydantic Request Models

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class DetailLevel(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"


class GenerateStudyGuideRequest(BaseModel):
    material_ids: list[str] = Field(..., min_length=1, max_length=20)
    focus_topics: list[str] = Field(default_factory=list, max_length=10)
    detail_level: DetailLevel = Field(default=DetailLevel.STANDARD)


class GenerateQuizRequest(BaseModel):
    material_ids: list[str] = Field(..., min_length=1, max_length=20)
    num_questions: int = Field(default=10, ge=5, le=25)
    difficulty: Difficulty = Field(default=Difficulty.MIXED)
    question_types: list[QuestionType] = Field(
        default=[QuestionType.MULTIPLE_CHOICE, QuestionType.SHORT_ANSWER]
    )


class QuizAnswer(BaseModel):
    question_id: str
    answer: str


class SubmitQuizRequest(BaseModel):
    answers: list[QuizAnswer] = Field(..., min_length=1)
```

### Pydantic Response Models

```python
class MaterialResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_url: str
    uploaded_at: datetime


class MaterialDetailResponse(MaterialResponse):
    preview_url: Optional[str] = None


class MaterialsListResponse(BaseModel):
    materials: list[MaterialResponse]


class UploadResponse(BaseModel):
    materials: list[MaterialResponse]


class KeyTerm(BaseModel):
    term: str
    definition: str


class StudyGuideSection(BaseModel):
    heading: str
    content: str
    key_terms: list[KeyTerm] = Field(default_factory=list)


class StudyGuide(BaseModel):
    id: str
    title: str
    summary: str
    sections: list[StudyGuideSection]
    source_materials: list[str]
    generated_at: datetime


class GenerationMetadata(BaseModel):
    model: str
    generation_time_ms: int
    material_count: int
    request_id: str


class StudyGuideResponse(BaseModel):
    study_guide: StudyGuide
    metadata: GenerationMetadata


class QuizQuestion(BaseModel):
    id: str
    type: QuestionType
    difficulty: Difficulty
    question: str
    options: list[str] = Field(default_factory=list)  # For multiple choice
    correct_answer: str
    explanation: str


class Quiz(BaseModel):
    id: str
    title: str
    questions: list[QuizQuestion]
    source_materials: list[str]
    generated_at: datetime


class QuizResponse(BaseModel):
    quiz: Quiz
    metadata: GenerationMetadata


class QuizScore(BaseModel):
    correct: int
    total: int
    percentage: float


class QuestionResult(BaseModel):
    question_id: str
    submitted_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class QuizSubmissionResponse(BaseModel):
    quiz_id: str
    score: QuizScore
    results: list[QuestionResult]
    submitted_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    model: str
    storage_bucket: str


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    value: Optional[str] = None
    reason: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
```

---

## Notes for Implementation

1. **File upload handling:** Use FastAPI's `UploadFile` type for multipart file uploads. Validate MIME types before uploading to Firebase Storage.

2. **Material IDs:** Generate unique material IDs using `uuid4()` prefixed with `mat_`. Similarly, study guide IDs use `sg_` prefix and quiz IDs use `qz_` prefix.

3. **CORS:** The FastAPI app must configure CORS middleware to allow requests from the Firebase Hosting domain and `localhost:5173` (Vite dev server).

4. **Request ID:** Generate a unique `request_id` per request using `uuid4()` prefixed with `req_`. This aids debugging in Cloud Run logs.

5. **Quiz grading:** Multiple choice questions are graded with exact match. Short answer questions should be graded by sending the student's answer and the correct answer to Gemini for semantic comparison, returning a boolean and explanation.

6. **In-memory storage:** For the MVP, generated study guides and quizzes can be stored in an in-memory dict keyed by ID. This means they are lost on server restart, which is acceptable for a portfolio project.

---

## Voice Coach Endpoints

### GET /api/v1/voice/status

Check voice mode availability, caps, and remaining sessions for the current device.

**Request Headers:**
- `X-Device-ID: string (1..64 chars)` (required)

**Response (200 OK):**
```json
{
  "enabled": true,
  "max_duration_s": 180,
  "sessions_per_device_per_day": 2,
  "remaining_today": 2,
  "model": "gemini-3.1-flash-live-preview"
}
```

---

### WS /api/v1/voice/session

Bidirectional WebSocket connection for live interactive voice coaching and oral quizzes powered by Gemini Live API.

**Handshake:**
- No query parameters or subprotocols required.
- `Origin` header validated against `ALLOWED_ORIGINS` when non-empty.

**Client → Server Messages:**

| Frame | Shape | Description |
|---|---|---|
| text | `{"type":"start","device_id":"<id>","study_guide":<StudyGuide>,"voice":"<optional>","num_questions":<optional 3..10>}` | First frame within 5s of accept. |
| text | `{"type":"speech_start"}` | Student pressed talk (ActivityStart). |
| binary | raw PCM16 LE, 16 kHz, mono (≤32768 bytes/frame) | Audio data forwarded to Live session. |
| text | `{"type":"speech_end"}` | Student released talk (ActivityEnd). |
| text | `{"type":"end"}` | Request normal session termination. |

**Server → Client Messages:**

| Frame | Shape | Description |
|---|---|---|
| text | `{"type":"ready","session_id":"vs_<8 hex>","max_duration_s":180,"ends_at":"<ISO UTC>","voice":"<name>"}` | Initial ready frame once session connected. |
| binary | raw PCM16 LE, 24 kHz, mono | Spoken audio chunks from coach. |
| text | `{"type":"transcript","role":"user"\|"coach","text":"<string>"}` | Real-time transcription chunks. |
| text | `{"type":"turn_complete"}` | Coach finished speaking a turn. |
| text | `{"type":"time_up","grace_s":30}` | Session time limit reached. Client input is locked from here on; the coach may finish its current turn for up to `grace_s` seconds, then `ended` follows with reason `max_duration`. |
| text | `{"type":"interrupted"}` | Coach turn interrupted by user. |
| text | `{"type":"answer_recorded","index":<1-based>,"question":"<string>","student_answer":"<string>","correct":<bool>,"feedback":"<string>","score":{"correct":<int>,"total":<int>}}` | Answer recorded during oral quiz. |
| text | `{"type":"quiz_summary","summary":"<string>","score":{"correct":<int>,"asked":<int>,"total":<int>}}` | Final summary and score after last question. |
| text | `{"type":"ended","reason":"client_end"\|"max_duration"\|"idle_timeout"\|"upstream_closed"\|"quiz_complete"}` | Normal end frame before close 1000. |
| text | `{"type":"error","code":"<CODE>","message":"<string>"}` | Error frame sent before close. |

**WebSocket Close Codes:**

| Code | Error Code | Description |
|---|---|---|
| 1000 | none | Normal termination after `ended`. |
| 1011 | `UPSTREAM_ERROR` | Live API upstream error. |
| 4400 | `BAD_MESSAGE`, `FRAME_TOO_LARGE`, `INVALID_STUDY_GUIDE`, `GUIDE_TOO_LARGE`, `INVALID_VOICE`, `INVALID_NUM_QUESTIONS` | Malformed or oversize client input. |
| 4401 | `INVALID_DEVICE_ID` | `device_id` missing, empty, or >64 characters. |
| 4403 | `ORIGIN_NOT_ALLOWED` | Origin check failed. |
| 4408 | `START_TIMEOUT` | No `start` frame within timeout. |
| 4429 | `DEVICE_DAILY_LIMIT`, `GLOBAL_DAILY_LIMIT`, `CONCURRENT_LIMIT`, `AUDIO_QUOTA_EXCEEDED` | Session or rate cap hit. |
| 4503 | `VOICE_DISABLED` | Feature flag `VOICE_ENABLED` is false. |

**Pacing:** after the coach records an answer and finishes its feedback turn, the server waits `VOICE_NEXT_QUESTION_PAUSE_SECONDS` (default 2.5) and then prompts the coach to ask the next question. A `speech_start` during the pause cancels the prompt.

**Live API Tool Declarations:**
- `record_answer`: parameters `question` (str), `student_answer` (str), `correct` (bool), `feedback` (str).
- `end_quiz`: parameters `summary` (str).

