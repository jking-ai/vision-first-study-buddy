# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

Vision-First Study Buddy is a multimodal study tool that consumes hand-written notes, whiteboard photos, PDFs, and epubs to generate personalized study guides and quizzes. It leverages Gemini 3.1 Pro's native vision capabilities and massive context window to process messy, real-world student materials without requiring manual transcription.

- **Backend:** FastAPI 0.115+ (Python 3.12) on Cloud Run
- **Frontend:** React 19 + MUI (Material UI) + Vite on Firebase Hosting
- **LLM:** Vertex AI Gemini 3.1 Pro (preview) via `google-cloud-aiplatform` SDK (native multimodal + 1M token context)
- **Storage:** Firebase Storage for uploaded images, PDFs, and epubs
- **Data:** No database -- uploaded materials are stored in Firebase Storage; generated content is returned directly to the client

**Status:** Phases 1-2 complete (backend fully implemented), Phase 3 (frontend) complete — all pages, components, and hooks implemented with material upload, camera capture, study guide generation, quiz taking/grading, and responsive UI with dark mode.

## Build & Run Commands

### Backend (`backend/` directory)
```bash
cd backend
pip install -r requirements.txt    # Install dependencies
uvicorn app.main:app --reload      # Local dev server on :8000
pytest                             # Run tests
docker build -t vfsb-backend .     # Build container
docker run -p 8000:8000 \
  -e GCP_PROJECT_ID=your-project \
  -e FIREBASE_STORAGE_BUCKET=your-project.appspot.com \
  vfsb-backend                     # Run container locally
```

**Required environment variables** (set in `backend/.env` or your shell):
- `GCP_PROJECT_ID` — GCP project ID (required; app fails to start without it)
- `FIREBASE_STORAGE_BUCKET` — Firebase Storage bucket (required; app fails to start without it)

See `backend/.env.example` for all variables.

### Frontend (`frontend/` directory)
```bash
cd frontend
npm install                        # Install dependencies
npm run dev                        # Dev server on :5173
npm run build                      # Production build to ./dist/
npm run preview                    # Preview production build
npm test                           # Run tests
```

**Frontend architecture:**
- **Pages:** HomePage, MaterialsPage, StudyGuidePage, QuizPage
- **Components:** TopNav, MaterialUpload (drag-drop), MaterialList (card grid with selection), CameraCapture (MediaDevices API), StudyGuideView (accordion sections), QuizView (taking + results modes)
- **Hooks:** useMaterials (fetch/refresh list), useUpload (validation + upload), useStudyGuide (generation), useQuiz (generation + submission)
- **Cross-page state:** Router state (`navigate('/path', { state: { selectedIds } })`) passes material selections between pages

### Deployment
```bash
# Backend: deploy to Cloud Run from source
gcloud run deploy vision-first-study-buddy \
  --source ./backend \
  --region us-central1 \
  --project <your-gcp-project> \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=<your-gcp-project>,FIREBASE_STORAGE_BUCKET=<your-storage-bucket>,ALLOWED_ORIGINS=[\"https://<your-firebase-site>.web.app\",\"https://<your-firebase-site>.firebaseapp.com\"]"

# Frontend: build and deploy to Firebase Hosting
cd frontend
VITE_API_URL=https://<your-cloud-run-url> npm run build
cd ..
firebase deploy --only hosting:study-buddy --project <your-gcp-project>
```

## Architecture

### Request Flow
`Browser (mobile/desktop)` -> `Firebase Hosting (React + MUI SPA)` -> `FastAPI (Cloud Run)` -> `Firebase Storage (file hosting)` + `Vertex AI Gemini 3.1 Pro (multimodal processing)` -> Structured JSON response -> `Frontend renders study guide / quiz`

### Key Design Decisions
- **Multimodal input:** Sends images and PDFs directly to Gemini 3.1 Pro as multimodal content parts. No separate OCR pipeline -- Gemini handles text extraction, diagram recognition, and content understanding in a single pass.
- **Long-context processing:** Leverages Gemini's 1M token context window to process multiple uploaded materials simultaneously, avoiding the complexity of chunking or vector-based RAG.
- **Firebase Storage:** Uploaded files are stored in Firebase Storage buckets, providing CDN-backed access and persistent URLs that can be passed to the Gemini API.
- **Mobile-first camera capture:** The frontend integrates with the device camera via the MediaDevices API, allowing students to snap photos of notes directly within the app.
- **No database:** Materials are stored in Firebase Storage with metadata in the file path structure. Generated study guides and quizzes are returned to the client and not persisted. This keeps the architecture simple for a portfolio project.

### API Endpoints
- `POST /api/v1/materials/upload` -- Upload images, PDFs, or epubs to Firebase Storage
- `GET /api/v1/materials` -- List uploaded materials
- `GET /api/v1/materials/{id}` -- Get material details and metadata
- `POST /api/v1/study-guides/generate` -- Generate a study guide from selected materials
- `GET /api/v1/study-guides/{id}` -- Retrieve a generated study guide
- `POST /api/v1/quizzes/generate` -- Generate a quiz from selected materials
- `GET /api/v1/quizzes/{id}` -- Retrieve a generated quiz
- `POST /api/v1/quizzes/{id}/submit` -- Submit quiz answers for grading
- `GET /api/v1/health` -- Health check and service metadata

## Environment Setup

```bash
cp backend/.env.example backend/.env
# Required variables:
#   GCP_PROJECT_ID=<your-gcp-project>
#   GCP_REGION=us-central1 (default)
#   GEMINI_MODEL=gemini-3.1-pro-preview (default)
#   FIREBASE_STORAGE_BUCKET=<your-storage-bucket>
```

Backend requires GCP credentials for Vertex AI Gemini and Firebase Storage. For local development, configure application default credentials or a service account key. In production, Cloud Run's service account (with "Vertex AI User" and "Storage Object Admin" roles) provides implicit auth.

## Project Documentation

Detailed specs live in `docs/`:
- [`docs/README.md`](docs/README.md) -- Documentation index and quick links
- [`docs/architecture.md`](docs/architecture.md) -- System architecture, tech stack, and design decisions
- [`docs/api-contracts.md`](docs/api-contracts.md) -- API endpoint specifications and Pydantic models
- [`docs/milestones.md`](docs/milestones.md) -- Development phases and deliverables
- [`docs/local-dev-guide.md`](docs/local-dev-guide.md) -- Local development setup
- [`docs/local-testing-guide.md`](docs/local-testing-guide.md) -- Testing guide (backend, API, frontend, manual)
- [`docs/production-deployment.md`](docs/production-deployment.md) -- GCP deployment guide
