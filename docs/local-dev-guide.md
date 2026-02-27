# Local Development Guide

How to set up, run, and develop Vision-First Study Buddy on your local machine.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Firebase CLI | 13+ | `firebase --version` |
| Google Cloud SDK | latest | `gcloud --version` |

---

## 1. Environment Setup

<!-- TODO: Add detailed environment setup steps once the project is scaffolded -->

```bash
# Clone the repository
git clone <repo-url>
cd vision-first-study-buddy

# Copy environment template
cp backend/.env.example backend/.env
# Fill in: GCP_PROJECT_ID, GCP_REGION, GEMINI_MODEL, FIREBASE_STORAGE_BUCKET
```

### GCP Credentials

<!-- TODO: Document credential setup for local Vertex AI and Firebase Storage access -->
<!-- Options: application default credentials or service account key -->
<!-- Service account needs: Vertex AI User, Storage Object Admin roles -->

---

## 2. Start the Backend

<!-- TODO: Add backend startup instructions once FastAPI app is created -->

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Verify Backend

```bash
curl http://localhost:8000/api/v1/health
```

---

## 3. Start the Frontend

<!-- TODO: Add frontend startup instructions once React app is scaffolded -->

```bash
cd frontend
npm install
npm run dev
# Vite dev server starts on http://localhost:5173
```

---

## 4. Quick Verification

<!-- TODO: Add end-to-end verification steps -->

1. Backend health check returns 200
2. Frontend loads in browser at `http://localhost:5173`
3. Upload an image file through the frontend
4. Generate a study guide from the uploaded material
5. Generate a quiz and submit answers

---

## Troubleshooting

<!-- TODO: Add common issues and solutions -->

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure virtual environment is activated and dependencies are installed |
| CORS errors in browser | Verify backend CORS config includes `http://localhost:5173` |
| Gemini authentication failure | Check GCP credentials: `gcloud auth application-default login` |
| Firebase Storage permission denied | Verify service account has Storage Object Admin role |
| Port already in use | Kill the existing process or use a different port |
| Camera not working in browser | Ensure the page is served over HTTPS or localhost (required for MediaDevices API) |
