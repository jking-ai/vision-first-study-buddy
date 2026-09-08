# Vision-First Study Buddy

**One-line summary:** A multimodal study tool that consumes hand-written notes, whiteboard photos, PDFs, and epubs -- then generates personalized study guides and quizzes using Gemini's native vision and long-context capabilities.

---

## Problem Statement

Students accumulate study materials in many formats -- handwritten lecture notes, whiteboard photos snapped during class, PDF textbooks, and epub readings. Turning these raw materials into effective study aids (condensed guides, practice quizzes) is time-consuming and often done poorly. Existing tools require clean digital text, ignoring the reality that most student notes are messy, handwritten, and mixed with diagrams. Students need a tool that can ingest their actual materials -- photos of notebook pages, whiteboard snapshots, annotated PDFs -- and produce structured study guides and quizzes without requiring manual transcription.

## Target User Persona

**Name:** Alex, a second-year university Biology student

- Takes handwritten notes during lectures because it improves retention
- Frequently photographs whiteboards before the professor erases them
- Has a mix of PDF textbook chapters and epub supplementary readings
- Spends 2-3 hours before each exam manually re-reading and summarizing notes
- Wants to quickly generate study guides that synthesize all materials for a topic
- Needs practice quizzes to test understanding, not just re-read highlights
- Uses their phone to capture notes, so the tool must be mobile-friendly

## Skills and Engineering Patterns Showcased

| Pattern | Description |
|---------|-------------|
| **Multimodal Computer Vision** | Processing handwritten notes, whiteboard photos, and diagrams through Gemini's native image understanding -- a high-value enterprise skill applicable to digitizing paper forms, technical blueprints, and medical records |
| **Long-Context Document Processing** | Leveraging Gemini 3.1 Pro's 1M token context window to process multiple documents simultaneously without chunking or traditional RAG pipelines |
| **File Upload Pipeline** | Handling multipart file uploads (images, PDFs, epubs) with Firebase Storage integration for persistent, CDN-backed storage |
| **Asynchronous Processing** | Managing long-running LLM generation tasks with status tracking and polling |
| **FastAPI Backend Design** | Clean REST API with Pydantic models, file upload handling, and proper error responses |
| **Mobile-First Web App** | React + MUI responsive design with camera capture integration for snapping photos of notes directly from the app |
| **Firebase Integration** | Firebase Storage for file hosting and Firebase Hosting for the frontend SPA |
| **Prompt Engineering for Extraction** | Crafting prompts that reliably extract structured information (key concepts, definitions, relationships) from messy visual inputs |
| **Cost-Aware API Hardening** | Per-IP rate limiting (slowapi) on every Vertex AI–backed endpoint, locked-down CORS, and disabled OpenAPI docs in production -- defending an unauthenticated, publicly-invokable Cloud Run service from cost-runaway abuse |

## Success Criteria

1. **Functional:** A user can upload a photo of handwritten notes and receive a structured study guide within 30 seconds.
2. **OCR Quality:** The system correctly extracts text from handwritten notes with at least 85% accuracy for legible handwriting, including recognition of common diagrams and formulas.
3. **Study Guide Quality:** Generated study guides contain key concepts, definitions, and relationships that a human reviewer would agree covers the source material.
4. **Quiz Quality:** Generated quizzes produce questions at multiple difficulty levels (recall, comprehension, application) that are answerable from the source material.
5. **Multi-Format Support:** The system accepts JPEG/PNG images, PDF documents, and epub files without requiring format-specific user actions.
6. **Mobile Usability:** The camera capture feature works on iOS Safari and Android Chrome, allowing students to snap and upload notes in under 5 seconds.
7. **Deployable:** The backend runs on Cloud Run and the frontend is hosted on Firebase Hosting, both accessible via public URLs.
8. **Portfolio-Ready:** The project README, architecture docs, and live demo clearly communicate the multimodal engineering decisions to a technical reviewer.
9. **Talking Tutor:** Say your answers out loud. The tutor asks questions from your study guide, replies with spoken feedback, and records a scored result in quiz history. Powered by the Gemini Live API.

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System design, tech stack, data flow, and design decisions |
| [API Contracts](docs/api-contracts.md) | Endpoint specs, request/response examples, Pydantic models |
| [Milestones](docs/milestones.md) | Development phases and deliverables |
| [Local Development Guide](docs/local-dev-guide.md) | Prerequisites, environment setup, running locally |
| [Local Testing Guide](docs/local-testing-guide.md) | Backend tests, API testing, manual testing |
| [Production Deployment](docs/production-deployment.md) | GCP deployment, Docker, Cloud Run, Firebase Hosting |

## Level of Effort

**Medium** -- Estimated 4-5 focused implementation sessions.

- Backend: ~6 hours (FastAPI setup, file upload pipeline, Gemini multimodal integration, study guide/quiz generation)
- Frontend: ~5 hours (React + MUI app, camera capture, file upload UI, study guide and quiz views)
- Deployment: ~2 hours (Dockerfile, Cloud Run deploy, Firebase Storage + Hosting)
- Polish: ~3 hours (mobile optimization, error handling, dark mode, loading states)
