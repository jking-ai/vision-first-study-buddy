# Production Deployment -- Vision-First Study Buddy

How to deploy and operate the application on Google Cloud Platform.

---

## GCP Resources

<!-- TODO: Fill in once infrastructure is provisioned -->

| Resource | Service | Details |
|----------|---------|---------|
| Backend API | Cloud Run | `vision-first-study-buddy` in `us-central1` |
| Frontend | Firebase Hosting | Static SPA served via CDN |
| LLM | Vertex AI | Gemini 1.5 Flash (`gemini-1.5-flash`) |
| File Storage | Firebase Storage | Images, PDFs, and epubs |
| Container Registry | Artifact Registry | Docker images for Cloud Run |

### Required IAM Roles

<!-- TODO: Document service account and IAM configuration -->

- Cloud Run service account needs **Vertex AI User** role for Gemini access
- Cloud Run service account needs **Storage Object Admin** role for Firebase Storage access

---

## Docker Build

<!-- TODO: Add Docker build commands once Dockerfile is created -->

```bash
cd backend

# Build the container image
docker build -t vfsb-backend .

# Test locally
docker run -p 8000:8000 \
  -e GCP_PROJECT_ID=your-project-id \
  -e GCP_REGION=us-central1 \
  -e FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com \
  vfsb-backend

# Tag and push to Artifact Registry
# docker tag vfsb-backend us-central1-docker.pkg.dev/<project>/vfsb/backend:latest
# docker push us-central1-docker.pkg.dev/<project>/vfsb/backend:latest
```

---

## Cloud Run Deployment

<!-- TODO: Add deployment commands once Cloud Run service is configured -->

```bash
# Deploy from source (simplest approach)
gcloud run deploy vision-first-study-buddy \
  --source ./backend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=your-project-id,GCP_REGION=us-central1,FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com"

# Verify deployment
curl https://vision-first-study-buddy-<hash>-uc.a.run.app/api/v1/health
```

---

## Firebase Hosting Deployment

<!-- TODO: Add Firebase hosting setup and deploy commands -->

```bash
cd frontend

# Build the production frontend
VITE_API_URL=https://vision-first-study-buddy-<hash>-uc.a.run.app npm run build

# Deploy to Firebase Hosting
firebase deploy --only hosting
```

### Firebase Configuration

<!-- TODO: Document firebase.json and hosting config -->
<!-- The frontend/firebase.json should configure dist/ as the public directory with SPA rewrite rules -->

---

## Verification

<!-- TODO: Add post-deployment verification checklist -->

1. **Backend health:** `curl https://<cloud-run-url>/api/v1/health` returns 200
2. **Upload endpoint:** POST a test image to `/api/v1/materials/upload` and verify it returns a material ID
3. **Study guide generation:** POST to `/api/v1/study-guides/generate` with the uploaded material ID
4. **Quiz generation:** POST to `/api/v1/quizzes/generate` and verify quiz questions are returned
5. **Frontend:** Firebase Hosting URL loads the React app
6. **End-to-end:** Upload a handwritten notes photo through the frontend, generate a study guide, and verify it displays

---

## Troubleshooting

<!-- TODO: Add production troubleshooting steps -->

| Issue | Solution |
|-------|----------|
| Cloud Run returns 500 | Check Cloud Run logs: `gcloud run services logs read vision-first-study-buddy` |
| CORS errors | Verify backend CORS config includes the Firebase Hosting domain |
| Gemini auth failure | Confirm service account has Vertex AI User role |
| Firebase Storage access denied | Confirm service account has Storage Object Admin role |
| Firebase deploy fails | Run `firebase use <project-id>` to set the active project |
| Large file upload timeout | Increase Cloud Run request timeout: `gcloud run services update --timeout 300` |
