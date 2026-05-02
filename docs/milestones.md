# Milestones -- Vision-First Study Buddy

## Phase 1: Foundation

**Goal:** Establish the project skeleton, confirm Firebase Storage and Vertex AI Gemini integration work end-to-end, and verify multimodal input processing.

**Estimated effort:** 2 sessions (~5 hours)

### Deliverables

#### 1.1 Backend Project Setup

**Acceptance criteria:**
- [ ] Python 3.12 project initialized with `requirements.txt` containing: `fastapi>=0.115`, `uvicorn`, `google-cloud-aiplatform`, `google-cloud-storage`, `firebase-admin`, `python-multipart`, `pydantic>=2.0`, `pydantic-settings>=2.0`, `python-dotenv`, `pytest`, `httpx`
- [ ] `Dockerfile` builds and runs locally with `docker build -t vfsb-backend . && docker run -p 8000:8000 vfsb-backend`
- [ ] `app/main.py` creates a FastAPI app instance with CORS middleware configured for `localhost:5173` and a placeholder production origin
- [ ] `app/config.py` loads settings from environment variables: `GCP_PROJECT_ID`, `GCP_REGION` (default: `us-central1`), `GEMINI_MODEL` (default: `gemini-3.1-pro-preview`), `FIREBASE_STORAGE_BUCKET`
- [ ] `GET /api/v1/health` returns the health response JSON as defined in api-contracts.md
- [ ] Running `uvicorn app.main:app --reload` starts the server without errors

#### 1.2 Firebase Storage Integration

**Acceptance criteria:**
- [ ] `app/services/storage_client.py` initializes Firebase Admin SDK with application default credentials
- [ ] The storage client can upload a file to the configured Firebase Storage bucket and return the storage URL
- [ ] The storage client can generate a signed URL for temporary read access to an uploaded file
- [ ] The storage client can list files in the materials directory
- [ ] A standalone test script (`scripts/test_storage.py`) uploads a test image and retrieves its signed URL, confirming Firebase Storage access works
- [ ] Error handling wraps Firebase exceptions and raises a custom `StorageError` with the original error message

#### 1.3 Vertex AI Gemini Multimodal Proof of Concept

**Acceptance criteria:**
- [ ] `app/services/gemini_client.py` initializes the Vertex AI SDK configured for the project and region from config
- [ ] A standalone test script (`scripts/test_gemini_multimodal.py`) sends a handwritten notes image to Gemini 3.1 Pro and prints the extracted text, confirming multimodal authentication works
- [ ] The client supports sending multiple content parts (images + text instructions) in a single call
- [ ] The client supports passing `response_mime_type="application/json"` for structured output
- [ ] Error handling wraps SDK exceptions and raises a custom `GenerationError` with the original error message
- [ ] Test is run 3 times with different handwriting samples to confirm consistency

**Dependencies:** 1.1 must be complete before 1.2 and 1.3.

---

## Phase 2: Core Features

**Goal:** Implement the full material upload pipeline, study guide generation, quiz generation, and quiz submission/grading.

**Estimated effort:** 2 sessions (~6 hours)

### Deliverables

#### 2.1 Material Upload Endpoint

**Acceptance criteria:**
- [x] `POST /api/v1/materials/upload` accepts multipart file uploads
- [x] File validation: rejects unsupported MIME types with `UNSUPPORTED_FILE_TYPE` error
- [x] File validation: rejects files over 20 MB with `FILE_TOO_LARGE` error
- [x] Accepted types: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`, `application/epub+zip`
- [x] Each file is uploaded to Firebase Storage under `materials/{material_id}/{filename}`
- [x] Returns a list of `MaterialResponse` objects with IDs, filenames, content types, sizes, and timestamps
- [x] `GET /api/v1/materials` returns all uploaded materials
- [x] `GET /api/v1/materials/{id}` returns a single material with a signed preview URL
- [x] Returns 404 with `MATERIAL_NOT_FOUND` for invalid material IDs

#### 2.2 Study Guide Generation

**Acceptance criteria:**
- [x] `app/prompts/study_guide_template.txt` contains a system instruction template that directs Gemini to: (a) analyze all provided materials including images and documents, (b) extract key concepts, definitions, and relationships, (c) organize content into logical sections, (d) identify and define key terms
- [x] `app/services/study_guide_generator.py` orchestrates: fetching materials from storage, building multimodal content parts, calling Gemini, parsing the structured response
- [x] `POST /api/v1/study-guides/generate` accepts a list of material IDs and optional focus topics
- [x] The endpoint fetches files from Firebase Storage and includes them as multimodal content parts (image bytes for images, PDF bytes for PDFs)
- [x] The `detail_level` parameter controls the depth of the generated guide (brief: 1-2 pages, standard: 3-5 pages, detailed: 5+ pages)
- [x] Returns a structured `StudyGuideResponse` with title, summary, sections (each with heading, content, key terms), and metadata
- [x] `GET /api/v1/study-guides/{id}` retrieves a previously generated study guide from in-memory storage
- [x] `metadata.generation_time_ms` accurately reflects the Gemini API call duration
- [x] On Gemini failure, returns 500 with `GENERATION_FAILED` error code

#### 2.3 Quiz Generation

**Acceptance criteria:**
- [ ] `app/prompts/quiz_template.txt` contains a system instruction template that directs Gemini to: (a) generate questions at the specified difficulty level(s), (b) create the specified question types (multiple choice, short answer, true/false), (c) include correct answers and explanations for each question, (d) base all questions on the provided source materials
- [ ] `app/services/quiz_generator.py` orchestrates: fetching materials, building multimodal prompt, calling Gemini, parsing quiz response
- [ ] `POST /api/v1/quizzes/generate` accepts material IDs, question count, difficulty, and question types
- [ ] Returns a structured `QuizResponse` with questions containing type, difficulty, question text, options (for multiple choice), correct answer, and explanation
- [ ] `GET /api/v1/quizzes/{id}` retrieves a previously generated quiz from in-memory storage
- [ ] Generated quizzes contain the requested number of questions (within +/- 1)
- [ ] Multiple choice questions have exactly 4 options labeled A-D

#### 2.4 Quiz Submission and Grading

**Acceptance criteria:**
- [ ] `POST /api/v1/quizzes/{id}/submit` accepts a list of question-answer pairs
- [ ] Multiple choice answers are graded with exact letter match (case-insensitive)
- [ ] Short answer questions are graded by sending the student answer and correct answer to Gemini for semantic comparison
- [ ] Returns a `QuizSubmissionResponse` with overall score (correct count, total, percentage) and per-question results (submitted answer, correct answer, is_correct, explanation)
- [ ] Returns 404 if the quiz ID does not exist
- [ ] Returns 400 if answers reference question IDs not in the quiz

**Dependencies:** 2.1 must be complete before 2.2 and 2.3. 2.3 must be complete before 2.4.

---

## Phase 3: Polish & Demo

**Goal:** Build the MUI frontend, add mobile camera capture, deploy to GCP, and ensure the project is portfolio-ready.

**Estimated effort:** 2 sessions (~5 hours)

### Deliverables

#### 3.1 Frontend -- Project Setup and Material Upload

**Acceptance criteria:**
- [x] React 19 project initialized with Vite and MUI: `npm create vite@latest frontend -- --template react`
- [x] MUI ThemeProvider configured with custom theme supporting light and dark modes
- [x] `src/api/client.js` exports an API client with methods for all backend endpoints
- [x] API base URL is configurable via `VITE_API_URL` environment variable (defaults to `http://localhost:8000`)
- [x] `TopNav.jsx` renders an app bar with navigation links and a dark mode toggle
- [x] `MaterialUpload.jsx` renders a drag-and-drop zone and file picker supporting images, PDFs, and epubs
- [x] Upload progress is shown with a progress bar
- [x] `MaterialList.jsx` displays uploaded materials as cards with file type icons (for documents)
- [x] `useMaterials.js` hook fetches and refreshes the materials list
- [x] `useUpload.js` hook handles file validation and upload with simulated progress

#### 3.2 Frontend -- Camera Capture

**Acceptance criteria:**
- [x] `CameraCapture.jsx` integrates with the device camera using the MediaDevices API (`navigator.mediaDevices.getUserMedia`)
- [x] Shows a live camera preview with a capture button
- [x] On capture, the photo is previewed and the user can accept or retake
- [x] Accepted photos are automatically uploaded via the materials upload endpoint
- [x] Falls back gracefully on devices without camera access (shows file picker instead)
- [x] Works on iOS Safari and Android Chrome
- [x] Materials page has tab toggle between Upload Files and Camera Capture

#### 3.3 Frontend -- Study Guide and Quiz Views

**Acceptance criteria:**
- [x] `StudyGuidePage.jsx` allows selecting materials and clicking "Generate Study Guide"
- [x] Loading state shows a spinner during generation
- [x] `StudyGuideView.jsx` renders the study guide with collapsible sections, key terms (bold + definition), and source/timestamp footer
- [x] `QuizPage.jsx` allows selecting materials, configuring quiz options (question count, difficulty, question types), and generating a quiz
- [x] `QuizView.jsx` renders questions as interactive cards -- radio buttons for multiple choice/true-false, text input for short answer
- [x] A submit button grades the quiz and shows results inline with color-coded correct/incorrect indicators and explanations
- [x] Error states display a clear message with retry/dismiss options

#### 3.4 Cloud Run and Firebase Hosting Deployment

**Acceptance criteria:**
- [ ] `Dockerfile` uses Python 3.12-slim base, installs dependencies, runs with `uvicorn`
- [ ] The container exposes port 8080 (Cloud Run default)
- [ ] `gcloud run deploy vision-first-study-buddy --source ./backend --region us-central1 --allow-unauthenticated` succeeds
- [ ] Cloud Run service account has `Vertex AI User` and `Storage Object Admin` IAM roles
- [ ] `firebase deploy --only hosting` deploys the frontend to Firebase Hosting
- [ ] CORS on the backend includes the Firebase Hosting domain
- [ ] `GET /api/v1/health` returns 200 from the deployed URL

#### 3.5 Dark Mode, Error Handling, and Project Documentation

**Acceptance criteria:**
- [x] Dark mode toggle in TopNav switches the entire app between light and dark themes
- [x] Responsive layout works on desktop (1200px+), tablet (768px+), and mobile (375px+) via MUI Grid2
- [x] All loading states show appropriate feedback (skeletons, spinners, progress bars)
- [x] All error states display user-friendly messages with retry/dismiss options
- [x] Empty states (no materials uploaded) show helpful onboarding messages with icons and CTAs
- [x] Print styles for study guides (hide nav, expand accordions)
- [ ] `README.md` is updated with live demo links, screenshots, setup instructions, and a "Technical Highlights" section
- [x] Planning docs (milestones.md) updated to reflect implementation status
- [x] Code includes JSDoc comments on all hooks and components

**Dependencies:** 3.1 must be complete before 3.2 and 3.3. 3.4 can run in parallel with 3.1-3.3 using local endpoints. 3.5 depends on all other Phase 3 deliverables.
