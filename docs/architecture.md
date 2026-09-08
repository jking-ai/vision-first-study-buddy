# Architecture -- Vision-First Study Buddy

## High-Level Service Architecture

```mermaid
graph TB
    User["User (Mobile/Desktop Browser)"]

    subgraph "Firebase Hosting"
        FE["React SPA<br/>Vite + React 19 + MUI"]
    end

    subgraph "Google Cloud Run"
        API["FastAPI Backend<br/>Python 3.12"]
    end

    subgraph "Firebase"
        Storage["Firebase Storage<br/>Images, PDFs, Epubs"]
    end

    subgraph "Vertex AI"
        Gemini["Gemini 3.1 Pro<br/>Multimodal Processing"]
    end

    User -->|"HTTPS"| FE
    User -->|"Camera capture"| FE
    FE -->|"REST API calls"| API
    API -->|"Upload files"| Storage
    API -->|"Fetch file URLs"| Storage
    API -->|"Multimodal content<br/>(images + text)"| Gemini
    API -->|"Returns structured JSON"| FE
```

## Flow Summary

### Material Upload Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as React Frontend
    participant API as FastAPI (Cloud Run)
    participant FS as Firebase Storage

    U->>FE: Select/capture files (photo, PDF, epub)
    FE->>API: POST /api/v1/materials/upload (multipart)
    API->>API: Validate file type and size
    API->>FS: Upload file to storage bucket
    FS-->>API: Return storage URL and metadata
    API-->>FE: 201 Created with material ID and metadata
    FE-->>U: Show uploaded material in list
```

### Study Guide Generation Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as React Frontend
    participant API as FastAPI (Cloud Run)
    participant FS as Firebase Storage
    participant LLM as Gemini 3.1 Pro

    U->>FE: Select materials and click "Generate Study Guide"
    FE->>API: POST /api/v1/study-guides/generate
    API->>FS: Fetch file content/URLs for selected materials
    FS-->>API: Return file data
    API->>API: Build multimodal prompt (images + text + instructions)
    API->>LLM: generate_content() with multimodal parts
    LLM-->>API: Structured study guide response
    API->>API: Parse and validate response
    API-->>FE: 200 OK with StudyGuide JSON
    FE-->>U: Render study guide with sections, key concepts, summaries
```

### Quiz Generation and Submission Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as React Frontend
    participant API as FastAPI (Cloud Run)
    participant FS as Firebase Storage
    participant LLM as Gemini 3.1 Pro

    U->>FE: Select materials and click "Generate Quiz"
    FE->>API: POST /api/v1/quizzes/generate
    API->>FS: Fetch file content/URLs for selected materials
    FS-->>API: Return file data
    API->>API: Build multimodal prompt for quiz generation
    API->>LLM: generate_content() with multimodal parts
    LLM-->>API: Structured quiz response (questions + answers)
    API-->>FE: 200 OK with Quiz JSON
    FE-->>U: Render quiz questions

    U->>FE: Answer questions and submit
    FE->>API: POST /api/v1/quizzes/{id}/submit
    API->>API: Grade answers against answer key
    API-->>FE: 200 OK with graded results
    FE-->>U: Show score and explanations
```

### Voice Coach Interactive Quiz Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as React Frontend (VoicePage)
    participant API as FastAPI Cloud Run Relay
    participant LIVE as Gemini Live API (Google GenAI)

    U->>FE: Click "Start Session" (user gesture creates AudioContexts)
    FE->>API: WS /api/v1/voice/session
    FE->>API: {"type":"start", "study_guide": {...}}
    API->>API: VoiceSessionGuard.acquire(device_id)
    API->>LIVE: client.aio.live.connect(model, config)
    API-->>FE: {"type":"ready", "session_id": "vs_...", "max_duration_s": 180}

    loop Push-to-Talk Turn
        U->>FE: Hold talk button (pointerdown / Space)
        FE->>API: {"type":"speech_start"}
        FE->>API: Binary PCM16 frames (16 kHz mono)
        API->>LIVE: send_realtime_input(audio=Blob)
        U->>FE: Release talk button (pointerup)
        FE->>API: {"type":"speech_end"}

        LIVE-->>API: Server content (output transcription + 24 kHz PCM audio)
        API-->>FE: {"type":"transcript", "role":"coach", "text":"..."}
        API-->>FE: Binary PCM16 frames (24 kHz) -> AudioContext queue
        LIVE-->>API: Tool call: record_answer(question, student_answer, correct, feedback)
        API-->>FE: {"type":"answer_recorded", "score": {...}, ...}
        API->>LIVE: send_tool_response(status="ok")
        LIVE-->>API: Turn complete
        API-->>FE: {"type":"turn_complete"}
    end

    LIVE-->>API: Tool call: end_quiz(summary="...")
    API-->>FE: {"type":"quiz_summary", "summary":"...", "score":{...}}
    API->>LIVE: send_tool_response(status="ok")
    FE->>FE: saveQuizResult({..., mode: "voice"})
    API-->>FE: {"type":"ended", "reason":"quiz_complete"}
    API->>API: VoiceSessionGuard.release(device_id) & log voice_session_end
```

## Tech Stack

| Service | Technology | Version | Rationale |
|---------|-----------|---------|-----------|
| **Backend API** | FastAPI | 0.115+ | Async-first Python framework with built-in OpenAPI docs, Pydantic integration, and native multipart file upload support |
| **Runtime** | Python | 3.12 | Stable release with full ecosystem support for google-cloud-aiplatform and firebase-admin SDKs |
| **LLM Access** | Vertex AI SDK (`google-cloud-aiplatform`) | latest | Official Google SDK for Vertex AI with native support for multimodal content (images, PDFs) and structured output |
| **Voice Live API** | Google GenAI SDK (`google-genai`) | 1.0+ | Official SDK for Gemini Live API bidirectional WebSocket streaming (`gemini-3.1-flash-live-preview`) |
| **WebSocket Server** | `websockets` | 13.0+ | High-performance WebSocket support for Uvicorn and FastAPI |
| **LLM Model** | Gemini 3.1 Pro | `gemini-3.1-pro-preview` | Native multimodal understanding (images, PDFs); 1M token context window enables processing multiple documents without chunking; stronger reasoning for messy handwriting, layout interpretation, and structured output |
| **Voice Model** | Gemini 3.1 Flash Live | `gemini-3.1-flash-live-preview` | Sub-second audio latency, native speech generation and transcription, tool use for oral quiz scoring |
| **File Storage** | Firebase Storage | N/A | CDN-backed object storage with simple upload/download APIs; integrates with Firebase Admin SDK for server-side access |
| **Frontend** | React | 19.x | Component-based UI with hooks for state management; broad ecosystem for camera/file APIs |
| **UI Framework** | MUI (Material UI) | 6.x | Pre-built accessible components (cards, buttons, dialogs, file inputs); responsive grid system for mobile-first design; built-in dark mode support |
| **Frontend Tooling** | Vite | 6.x | Fast dev server with HMR; optimized production builds; first-class React support |
| **Frontend Hosting** | Firebase Hosting | N/A | CDN-backed static hosting with custom domain support; co-located with Firebase Storage |
| **Container Runtime** | Cloud Run | N/A | Serverless containers with automatic scaling; native IAM for Vertex AI and Firebase access |
| **Containerization** | Docker | N/A | Standard OCI container for reproducible builds and Cloud Run deployment |
| **Data Validation** | Pydantic | 2.x | Schema enforcement for API request/response models; used by FastAPI natively |

## Key Design Decisions and Trade-offs

### 1. Gemini Native Vision vs. Separate OCR Pipeline

**Decision:** Use Gemini 3.1 Pro's built-in multimodal understanding instead of a dedicated OCR service (e.g., Google Cloud Vision API, Tesseract).

**Rationale:** Gemini 3.1 Pro natively accepts images and PDFs as input content parts. Rather than running OCR to extract text and then sending that text to an LLM, we send the raw images directly. This has several advantages: (a) Gemini understands spatial layout, diagrams, and annotations that pure OCR would lose, (b) fewer services to manage and pay for, (c) the model can reason about visual elements (arrows, underlines, diagrams) alongside text. The trade-off is that Gemini's text extraction may be less precise than dedicated OCR for very messy handwriting, but the holistic understanding compensates.

### 2. Long-Context Processing vs. RAG

**Decision:** Pass all uploaded materials into a single Gemini call using the 1M token context window, rather than implementing a retrieval-augmented generation (RAG) pipeline with embeddings and vector search.

**Rationale:** For the typical student use case (5-20 pages of notes, a few textbook chapters), the total content fits well within Gemini's context window. This eliminates the need for an embedding model, vector database, chunking strategy, and retrieval logic -- reducing architectural complexity significantly. The trade-off is that very large document sets (hundreds of pages) may exceed the context window or increase latency, but this is an acceptable limitation for a study tool.

### 3. Firebase Storage for File Hosting

**Decision:** Store uploaded files in Firebase Storage rather than Cloud Storage (GCS) directly.

**Rationale:** Firebase Storage provides a simpler SDK for both server-side (Firebase Admin) and client-side operations. It includes built-in CDN distribution, security rules, and integrates cleanly with the Firebase Hosting frontend. The underlying infrastructure is GCS, so there is no performance trade-off. Firebase Storage also provides signed URLs for temporary access, which is useful for passing file references to the Gemini API.

### 4. MUI for Mobile-First Design

**Decision:** Use Material UI (MUI) instead of a custom CSS framework or Tailwind CSS.

**Rationale:** MUI provides a comprehensive set of pre-built, accessible components that follow Material Design guidelines. The responsive grid system and breakpoint utilities make mobile-first development straightforward. Built-in dark mode support via the theme provider reduces custom CSS. For a study tool that students will primarily use on their phones, the native-feeling Material Design components (FABs, bottom sheets, cards) create a familiar mobile experience.

### 5. No Database

**Decision:** No persistent database. Materials are stored in Firebase Storage; generated study guides and quizzes are returned to the client and not persisted server-side.

**Rationale:** This is a portfolio project focused on demonstrating multimodal AI capabilities. Adding Firestore would increase complexity without showcasing new engineering patterns. If persistence is needed later (saving quiz history, tracking study progress), a Firestore collection can be added without architectural changes.

### 6. Synchronous Generation (No Job Queue)

**Decision:** Study guide and quiz generation are synchronous API calls rather than async jobs with polling.

**Rationale:** Generation completes in a single request-response cycle, which is simpler to implement and test. The frontend shows a loading state during generation. Gemini 3.1 Pro is slower than the Flash tier in exchange for stronger reasoning on handwriting and structured output; if generation times grow further (e.g., processing very large document sets), the architecture can be extended to use Cloud Tasks or Pub/Sub for async processing without changing the API contract.

## Project Source Code Structure

### Backend (`/backend`)

```
backend/
  Dockerfile
  requirements.txt
  .env.example
  app/
    __init__.py
    main.py                         # FastAPI app factory, CORS config, router mounting
    config.py                       # Settings via pydantic-settings (project ID, bucket, model, voice caps)
    rate_limit.py                   # slowapi per-IP limits & voice caps documentation
    dependencies.py                 # Dependency injection (storage, gemini, live_client, device_id)
    routers/
      upload.py                     # POST /api/v1/materials/upload
      materials.py                  # GET /api/v1/materials, GET /api/v1/materials/{id}
      study_guides.py               # POST /api/v1/study-guides/generate, GET /api/v1/study-guides/{id}
      quizzes.py                    # POST/GET /api/v1/quizzes endpoints
      voice.py                      # WS /api/v1/voice/session, GET /api/v1/voice/status
      health.py                     # GET /api/v1/health
    models/
      requests.py                   # Pydantic models for API request bodies
      responses.py                  # Pydantic models for API response bodies
      schemas.py                    # Shared data schemas (Material, StudyGuide, Quiz, etc.)
    services/
      material_processor.py         # File validation, metadata extraction, content preparation
      study_guide_generator.py      # Orchestrates study guide prompt building + Gemini call
      quiz_generator.py             # Orchestrates quiz prompt building + Gemini call
      gemini_client.py              # Wraps Vertex AI SDK initialization and multimodal generate calls
      live_client.py                # Wraps Google GenAI Live API client & session abstraction
      voice_guard.py                # In-memory daily and concurrency spend caps
      voice_session.py              # WebSocket relay, push-to-talk coordinator, tool execution
      storage_client.py             # Firebase Storage upload, download, URL generation
    prompts/
      study_guide_template.txt      # System instruction template for study guide generation
      quiz_template.txt             # System instruction template for quiz generation
      voice_coach_template.txt      # System instruction template for oral quiz voice coach
  scripts/
    voice_smoke.py                  # Smoke test for WebSocket live relay
  tests/
    test_voice.py                   # Full suite of unit & integration tests for voice mode
    fixtures/
      sample_study_guide.json       # Fixture for study guide JSON
      hello_16k.pcm                 # Synthetic 16kHz PCM audio fixture
```

### Frontend (`/frontend`)

```
frontend/
  index.html
  package.json
  vite.config.js                    # Vite configuration with WebSocket proxy and Vitest
  public/
    worklets/
      pcm-recorder.worklet.js       # AudioWorklet processor for raw mic capture
  src/
    main.jsx                        # React entry point
    App.jsx                         # Root component with MUI ThemeProvider and routing
    theme.js                        # MUI theme configuration (light/dark mode)
    api/
      client.js                     # Fetch wrapper for backend API calls (incl. getVoiceStatus)
    components/
      MaterialUpload.jsx            # Drag-and-drop + file picker upload component
      MaterialList.jsx              # Grid/list of uploaded materials with thumbnails
      StudyGuideView.jsx            # Rendered study guide with sections and highlights
      QuizView.jsx                  # Interactive quiz with question cards and answer inputs
      CameraCapture.jsx             # Camera integration for snapping photos of notes
      VoiceControls.jsx             # Hold-to-talk button, countdown timer, end session
      VoiceTranscript.jsx           # Real-time dialogue transcript
      VoiceScorePanel.jsx           # Running oral quiz score chip and per-question feedback
      TopNav.jsx                    # App bar with navigation and dark mode toggle
    pages/
      HomePage.jsx                  # Landing page with upload CTA and 4 step cards
      MaterialsPage.jsx             # Material management and selection view
      StudyGuidePage.jsx            # Study guide generation and "Quiz me by voice" CTA
      QuizPage.jsx                  # Quiz generation, taking, results, and voice history chip
      VoicePage.jsx                 # Voice Coach session interface
    hooks/
      useUpload.js                  # Custom hook for file upload with progress tracking
      useStudyGuide.js              # Custom hook for study guide generation with loading state
      useQuiz.js                    # Custom hook for quiz generation and submission
      useVoiceSession.js            # Custom hook managing WebSocket, mic stream, and 24kHz audio queue
    utils/
      pcm.js                        # Downsampling to 16kHz and Int16 PCM conversion
      voiceProtocol.js              # State reducer and error code mappings for voice sessions
      quizHistory.js                # Quiz history storage supporting written and voice modes
    styles/
      global.css                    # Global styles, CSS variables, font imports
```
