# Local Testing Guide

How to run tests, test the API manually, and verify frontend behavior.

---

## 1. Backend Tests

<!-- TODO: Add test commands once test suite is created -->

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_upload.py

# Run with coverage
pytest --cov=app
```

### Test Structure

<!-- TODO: Document test classes and what they cover -->
<!-- Expected test areas: material upload, study guide generation, quiz generation, quiz grading, Pydantic validation -->

---

## 2. API Testing (curl examples)

<!-- TODO: Update curl examples once endpoints are implemented -->

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Upload a Material

```bash
curl -X POST http://localhost:8000/api/v1/materials/upload \
  -F "files=@test-notes.jpg"
```

### List Materials

```bash
curl http://localhost:8000/api/v1/materials
```

### Get Material Details

```bash
curl http://localhost:8000/api/v1/materials/mat_a1b2c3d4
```

### Generate a Study Guide

```bash
curl -X POST http://localhost:8000/api/v1/study-guides/generate \
  -H "Content-Type: application/json" \
  -d '{
    "material_ids": ["mat_a1b2c3d4"],
    "detail_level": "standard"
  }'
```

### Generate a Quiz

```bash
curl -X POST http://localhost:8000/api/v1/quizzes/generate \
  -H "Content-Type: application/json" \
  -d '{
    "material_ids": ["mat_a1b2c3d4"],
    "num_questions": 5,
    "difficulty": "mixed"
  }'
```

### Submit Quiz Answers

```bash
curl -X POST http://localhost:8000/api/v1/quizzes/qz_m1n2o3p4/submit \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": "q1", "answer": "B"},
      {"question_id": "q2", "answer": "Mitosis produces identical cells."}
    ]
  }'
```

---

## 3. Frontend Testing

<!-- TODO: Add frontend test commands once test framework is configured -->

```bash
cd frontend

# Run tests (Vitest)
npm test

# Run with watch mode
npm run test:watch
```

---

## 4. Manual Testing

<!-- TODO: Add manual testing checklist -->

### Upload Validation

- [ ] Upload a JPEG image and verify it appears in the materials list
- [ ] Upload a PNG image and verify it appears in the materials list
- [ ] Upload a PDF and verify it appears in the materials list
- [ ] Attempt to upload an unsupported file type (e.g., .zip) and verify error message
- [ ] Attempt to upload a file over 20 MB and verify error message

### Study Guide Generation

- [ ] Generate a study guide from a single handwritten notes image
- [ ] Generate a study guide from a PDF textbook chapter
- [ ] Generate a study guide from multiple materials simultaneously
- [ ] Test with focus_topics parameter and verify the guide emphasizes those topics
- [ ] Test each detail_level (brief, standard, detailed) and verify output length varies

### Quiz Generation and Grading

- [ ] Generate a quiz with 5 multiple choice questions
- [ ] Generate a quiz with mixed question types (multiple choice + short answer)
- [ ] Verify multiple choice questions have exactly 4 options (A-D)
- [ ] Submit correct answers and verify 100% score
- [ ] Submit incorrect answers and verify explanations are provided
- [ ] Test with each difficulty level (easy, medium, hard, mixed)

### Mobile Camera Capture

- [ ] Open the app on a mobile device and verify camera capture works
- [ ] Capture a photo and verify it uploads successfully
- [ ] Verify the camera UI works on iOS Safari
- [ ] Verify the camera UI works on Android Chrome
- [ ] Verify fallback to file picker on devices without camera access
