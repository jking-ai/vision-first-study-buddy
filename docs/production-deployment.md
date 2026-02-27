# Production Deployment -- Vision-First Study Buddy

How to deploy and operate the application on Google Cloud Platform.

---

## GCP Resources

| Resource | Service | Details |
|----------|---------|---------|
| GCP Project | `<your-gcp-project>` | All resources live in this project |
| Backend API | Cloud Run | `vision-first-study-buddy` in `us-central1` |
| Backend URL | Cloud Run | `https://<your-cloud-run-url>` |
| Frontend | Firebase Hosting | `https://<your-firebase-site>.web.app` |
| Frontend (alt) | Firebase Hosting | `https://<your-firebase-site>.firebaseapp.com` |
| LLM | Vertex AI | Gemini 2.5 Flash (`gemini-2.5-flash`) |
| File Storage | Firebase Storage | Bucket: `<your-storage-bucket>` |
| Container Registry | Artifact Registry | `us-central1-docker.pkg.dev/<your-gcp-project>/cloud-run-source-deploy` |

### Required IAM Roles

- Cloud Run service account needs **Vertex AI User** role for Gemini access
- Cloud Run service account needs **Storage Object Admin** role for Firebase Storage access

### Environment Variables (Cloud Run)

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | `<your-gcp-project>` |
| `FIREBASE_STORAGE_BUCKET` | `<your-storage-bucket>` |
| `ALLOWED_ORIGINS` | `["https://<your-firebase-site>.web.app","https://<your-firebase-site>.firebaseapp.com"]` |

---

## Docker Build

```bash
cd backend

# Build the container image
docker build -t vfsb-backend .

# Test locally
docker run -p 8000:8000 \
  -e GCP_PROJECT_ID=<your-gcp-project> \
  -e GCP_REGION=us-central1 \
  -e FIREBASE_STORAGE_BUCKET=<your-storage-bucket> \
  vfsb-backend

# Tag and push to Artifact Registry
docker tag vfsb-backend us-central1-docker.pkg.dev/<your-gcp-project>/cloud-run-source-deploy/vision-first-study-buddy:latest
docker push us-central1-docker.pkg.dev/<your-gcp-project>/cloud-run-source-deploy/vision-first-study-buddy:latest
```

---

## Cloud Run Deployment

```bash
# Deploy from source (simplest approach -- builds and deploys in one step)
gcloud run deploy vision-first-study-buddy \
  --source ./backend \
  --region us-central1 \
  --project <your-gcp-project> \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=<your-gcp-project>,FIREBASE_STORAGE_BUCKET=<your-storage-bucket>,ALLOWED_ORIGINS=[\"https://<your-firebase-site>.web.app\",\"https://<your-firebase-site>.firebaseapp.com\"]"

# Verify deployment
curl https://<your-cloud-run-url>/api/v1/health
```

---

## Firebase Hosting Deployment

```bash
cd frontend

# Build the production frontend (API URL points to Cloud Run)
VITE_API_URL=https://<your-cloud-run-url> npm run build

# Deploy to Firebase Hosting (uses "study-buddy" target from .firebaserc)
cd ..
firebase deploy --only hosting:study-buddy --project <your-gcp-project>
```

### Firebase Configuration

- **`.firebaserc`** maps the `study-buddy` hosting target to your Firebase Hosting site
- **`firebase.json`** serves `frontend/dist/` as the public directory with SPA rewrite rules (all routes -> `index.html`)

---

## Full Deploy (Both Backend and Frontend)

```bash
# 1. Deploy backend to Cloud Run
gcloud run deploy vision-first-study-buddy \
  --source ./backend \
  --region us-central1 \
  --project <your-gcp-project> \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=<your-gcp-project>,FIREBASE_STORAGE_BUCKET=<your-storage-bucket>,ALLOWED_ORIGINS=[\"https://<your-firebase-site>.web.app\",\"https://<your-firebase-site>.firebaseapp.com\"]"

# 2. Build frontend
cd frontend
VITE_API_URL=https://<your-cloud-run-url> npm run build
cd ..

# 3. Deploy frontend to Firebase Hosting
firebase deploy --only hosting:study-buddy --project <your-gcp-project>
```

---

## Verification

1. **Backend health:** `curl https://<your-cloud-run-url>/api/v1/health` returns 200
2. **Upload endpoint:** POST a test image to `/api/v1/materials/upload` with `X-Device-ID` header and verify it returns a material ID
3. **Study guide generation:** POST to `/api/v1/study-guides/generate` with the uploaded material ID
4. **Quiz generation:** POST to `/api/v1/quizzes/generate` and verify quiz questions are returned
5. **Frontend:** `https://<your-firebase-site>.web.app` loads the React app
6. **End-to-end:** Upload a handwritten notes photo through the frontend, generate a study guide, and verify it displays

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cloud Run returns 500 | Check Cloud Run logs: `gcloud run services logs read vision-first-study-buddy --project <your-gcp-project>` |
| CORS errors | Verify `ALLOWED_ORIGINS` env var includes the Firebase Hosting domain |
| Gemini auth failure | Confirm service account has Vertex AI User role |
| Firebase Storage access denied | Confirm service account has Storage Object Admin role |
| Firebase deploy fails | Run `firebase use <your-gcp-project>` to set the active project |
| Large file upload timeout | Increase Cloud Run request timeout: `gcloud run services update vision-first-study-buddy --timeout 300 --project <your-gcp-project>` |
| Missing X-Device-ID header | All API requests (except `/health`) require the `X-Device-ID` header for device isolation |
