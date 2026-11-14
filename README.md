# AI Notes Summarizer with Quiz Generation and Multilingual Translator

An intelligent educational platform that assists students in mastering complex study materials through AI-powered multi-level text summarization, 4 interactive quiz formats (True/False, One-Word, MCQ, Fill-in-the-Blanks), and multilingual translation across 9 languages.

---

## 1. Project Introduction

Modern education exposes students to voluminous academic texts, lecture slides, assignments, and research articles. Comprehending, retaining, and self-evaluating across vast coursework leads to cognitive fatigue. 

**AI Notes Summarizer** provides an automated, AI-driven workflow:
1. Ingests textbooks and notes (PDF, DOCX, TXT, or direct text paste).
2. Distills core knowledge via abstractive summarization into **Short**, **Medium**, or **Detailed** notes with key definition callouts and takeaways.
3. Generates 4 distinct interactive quiz formats to reinforce active recall and test comprehension.
4. Translates summarized notes into 9 languages (English, Tamil, Hindi, Telugu, Malayalam, Kannada, French, Spanish, German) for native language accessibility.
5. Records learning history and visualizes study progress through a personalized analytics dashboard.

---

## 2. Project Features

- **Document Text Ingestion:** Seamless PDF (PyMuPDF), DOCX (python-docx), and TXT file parsing with OCR capability for scanned documents.
- **Multi-Level AI Summarization:** Short (high-yield points), Medium (balanced conceptual overview), and Detailed (definitions, examples, and comprehensive coverage).
- **Interactive Quiz Engine:**
  - True / False questions with factual explanations.
  - One-Word conceptual recall questions with normalized text comparison.
  - Multiple Choice Questions (MCQ) with 4 options and plausible distractors.
  - Fill in the Blanks with context-specific single-token blanks.
- **Multilingual Translation:** High-fidelity translation supporting Tamil, Hindi, Telugu, Malayalam, Kannada, French, Spanish, German, and English.
- **User Dashboard & Analytics:** Chart.js powered tracking of quiz scores, activity frequency, and document processing volume.
- **Enterprise-Grade Security:** JWT authentication, bcrypt/PBKDF2 password hashing, file-type verification, and isolated tenant storage.

---

## 3. Technology Stack

### Frontend
- **Markup & Layout:** HTML5, CSS3, Bootstrap 5.3.3
- **Scripting:** Modern JavaScript (ES6+ Modules, Fetch API)
- **Data Visualization:** Chart.js
- **Typography & Icons:** Google Plus Jakarta Sans, Inter, Bootstrap Icons

### Backend
- **Framework:** Python 3.11+ / Flask 3.0+ (Application Factory Pattern)
- **ORM & Migrations:** Flask-SQLAlchemy 3.1+, Flask-Migrate 4.1+, Alembic
- **Authentication:** Flask-JWT-Extended 4.6+
- **CORS & Middleware:** Flask-CORS 4.0+
- **Serving & WSGI:** Gunicorn (Linux/Docker) / Werkzeug (Local Development)

### Database
- **Development:** SQLite 3 (zero-configuration local persistence)
- **Production Support:** MySQL 8.0+ via PyMySQL and SQLAlchemy

### AI & NLP Pipeline
- **Summarization:** DistilBART (`sshleifer/distilbart-cnn-12-6`) with map-reduce recursive chunking
- **Quiz Generation:** FLAN-T5 (`google/flan-t5-base`) & deterministic NLP concept synthesizer
- **Translation:** `deep-translator` & MarianMT / NLLB-200 adapter
- **Document Processing:** PyMuPDF, python-docx, pytesseract

### Document Processing & Text Extraction (Phase 5)
- **Multi-Format Extraction:** Native support for PDF (`PyMuPDF`), Word DOCX (`python-docx`), Plain Text (`utf-8`, BOM, Tamil Unicode), and Images (`PNG`, `JPG`, `JPEG`).
- **Targeted OCR Engine:** Tesseract integration with image preprocessing (contrast enhancement, grayscale, sharpening) and multi-language support (`eng+tam`). Only scanned PDF pages trigger OCR, preserving speed.
- **Enterprise File Validation:** MIME validation, magic-byte signature matching, path traversal protection, UUID-based secure storage, and configurable size limits (default 20MB).
- **Text Cleaning & Quality Scoring:** Unicode NFKC normalization, whitespace standardization, sentence boundary correction, and automated quality classification (`HIGH`, `MEDIUM`, `LOW`, `FAILED`).

---

## 4. Folder Structure

```
AINotes/
├── frontend/                         # Client User Interface
│   ├── index.html                    # Public Landing & Health Status Page
│   ├── login.html                    # Student Sign-In View
│   ├── register.html                 # Student Registration View
│   ├── css/
│   │   ├── style.css                 # Global theme & typography
│   │   ├── auth.css                  # Authentication card styles
│   │   ├── dashboard.css             # Dashboard widgets & charts
│   │   └── responsive.css            # Responsive layout breakpoints
│   ├── js/
│   │   ├── config.js                 # API base URL & storage keys
│   │   ├── api.js                    # Reusable Fetch API client
│   │   └── main.js                   # UI utilities, password toggle & health pings
│   └── assets/
│       ├── images/                   # Static imagery
│       └── icons/                    # Custom application icons
│
├── backend/                          # RESTful API Application
│   ├── app/
│   │   ├── __init__.py               # Flask Application Factory
│   │   ├── config.py                 # Multi-environment configuration profiles
│   │   ├── extensions.py             # db, migrate, jwt, cors instances
│   │   ├── models/                   # SQLAlchemy Data Models
│   │   ├── routes/                   # API Blueprint Routes
│   │   │   ├── __init__.py
│   │   │   └── health_routes.py      # /api/ and /api/health endpoints
│   │   ├── services/                 # Business logic services
│   │   ├── ai/                       # Hugging Face AI pipeline singletons
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── error_handlers.py     # Centralized JSON error responses
│   │   └── middleware/               # Auth & security guards
│   ├── migrations/                   # Alembic database migrations
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # In-memory test client fixtures
│   │   └── test_health.py            # Automated health & API tests
│   ├── uploads/                      # Secure file upload storage
│   ├── logs/                         # Rotating application log files
│   ├── requirements.txt              # Python package dependencies
│   └── run.py                        # WSGI entry point
│
├── .env                              # Active environment variables (gitignored)
├── .env.example                      # Template environment variables
├── .gitignore                        # Git exclusion rules
├── Dockerfile                        # Multi-stage production container
├── docker-compose.yml                # Docker compose orchestration
└── README.md                         # Project documentation
```

---

## 5. Prerequisites

Before setting up the project, ensure you have:
- **Python 3.11+** installed (`python --version`)
- **Git** installed (`git --version`)
- A modern web browser (Chrome, Edge, Firefox, Safari)
- Optional: **Docker Desktop** (if deploying via containers)

---

## 6. Python Environment Setup (Windows & macOS/Linux)

### Windows (PowerShell):
```powershell
# Navigate to the project root
cd C:\Users\Rajesh Yuvaraja\AINotes

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 7. Dependency Installation

Install the required core packages using pip:

```powershell
pip install -r backend/requirements.txt
```

---

## 8. Environment Variable Setup

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Verify or customize variables inside `.env`:
```ini
FLASK_ENV=development
FLASK_APP=backend/run.py
SECRET_KEY=your-secure-secret-key-at-least-32-chars
PORT=5000
DATABASE_URL=sqlite:///ainotes.db
JWT_SECRET_KEY=your-secure-jwt-key
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH_MB=15
```

---

## 9. Database Setup & Initialization

The project initializes an SQLite database (`backend/ainotes.db`) automatically upon the first query check.

To verify or initialize migrations:
```powershell
# Set FLASK_APP environment variable
$env:FLASK_APP = "backend/run.py"

# Initialize migration repository (first time only)
flask db init -d backend/migrations

# Create migration from models
flask db migrate -d backend/migrations -m "Create application database schema"

# Apply migration to database
flask db upgrade -d backend/migrations
```

For complete database schema, data dictionary, and Mermaid ER diagram, refer to [docs/database.md](file:///c:/Users/Rajesh%20Yuvaraja/AINotes/docs/database.md).

---

## 9.1. Authentication REST Endpoints

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | No | Register new student with password complexity rules |
| `POST` | `/api/auth/login` | No | Authenticate credentials and receive JWT access token |
| `POST` | `/api/auth/logout` | Yes (Bearer) | Invalidate current session and revoke JWT in blocklist |
| `GET` | `/api/auth/me` | Yes (Bearer) | Retrieve safe profile of authenticated user |
| `PUT` | `/api/auth/profile` | Yes (Bearer) | Update name or email with duplicate prevention |
| `POST` | `/api/auth/change-password` | Yes (Bearer) | Change password requiring current password verification |

---

## 10. Running the Backend Server

Start the Flask development server on port 5000:

```powershell
python backend/run.py
```

Console Output:
```
[2026-11-11 19:06:42] INFO in backend.app: Application initialized successfully in development mode
 * Starting AI Notes Summarizer Backend in 'development' mode on http://127.0.0.1:5000
 * Running on http://127.0.0.1:5000
```

---

## 11. Running the Frontend

The frontend is built using standard HTML5/CSS3/JavaScript. You can open `frontend/index.html` directly in your browser or serve it using Python's built-in HTTP server:

```powershell
# Open a new terminal window
cd frontend
python -m http.server 8080
```

Open your browser and navigate to:
```
http://127.0.0.1:8080/index.html
```

The top status banner on the landing page will automatically ping the backend at `http://127.0.0.1:5000/api/health` and display:
- **API: Online** (Green badge)
- **DB: Connected** (Green badge)

---

## 12. API Health Check Verification

You can query the health endpoint using `curl` or PowerShell `Invoke-RestMethod`:

```powershell
# Test health endpoint
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" | ConvertTo-Json
```

Expected JSON Response:
```json
{
  "database": "connected",
  "message": "AI Notes Summarizer API is running",
  "status": "success"
}
```

```powershell
# Test API root metadata
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/" | ConvertTo-Json
```

Expected JSON Response:
```json
{
  "documentation": "/api/docs",
  "environment": "active",
  "service": "AI Notes Summarizer with Quiz Generation and Multilingual Translator API",
  "status": "success",
  "version": "1.0.0"
}
```

---

## 13. Automated Testing Instructions

Run the automated test suite across all completed modules using `pytest`:

```powershell
pytest backend/tests -v
```

Total Verified Test Suite:
- **201 / 201 Tests Passing (100%)**
- Zero failures, zero warnings, cross-phase regression verified across Phases 1 through 9.

---

## 14. Phase 7: Interactive Quiz Generation & Assessment Engine

Phase 7 provides an intelligent assessment synthesis engine supporting four question formats and three difficulty tiers derived directly from uploaded notes or summaries:

### Supported Question Types
1. **Multiple Choice Questions (MCQ):** 4 distinct options, exactly 1 correct answer, 3 plausible distractors, and an explanatory justification.
2. **True or False:** Factual statements with normalized truth values and explanations.
3. **One-Word Answer:** Targeted concept identification with case-insensitive and punctuation-normalized evaluation.
4. **Fill in the Blanks:** Contextual sentences with masked keywords (`______`) and normalized verification.

### Difficulty Levels
- **Easy:** Basic definitions, direct factual recall, and simple terminology.
- **Medium:** Conceptual understanding, comparisons, and structural relationships.
- **Hard:** Multi-concept analytical reasoning and complex application-based inquiries.

### Authenticated Quiz REST Endpoints
- `POST /api/quizzes/generate`: Generates questions from document/summary text (omits correct answers).
- `GET /api/quizzes/<id>`: Retrieves active quiz questions without answer keys.
- `GET /api/quizzes`: Returns paginated user quizzes with filters (`document_id`, `difficulty`, `quiz_type`).
- `POST /api/quizzes/<id>/submit`: Evaluates submitted answers server-side, stores attempt and responses, and returns detailed results.
- `GET /api/quizzes/attempts/<id>`: Retrieves full breakdown of an attempt including user vs correct answers.
- `GET /api/quizzes/history`: Lists user's quiz attempt history.
- `DELETE /api/quizzes/<id>`: Safely removes quiz and cascaded attempts.

---

## 15. Phase 8: Multilingual Translator Engine

Phase 8 introduces a production-ready multilingual translation system that translates AI-generated summaries into 9 target languages while preserving technical terminology, academic clarity, and structural formatting:

### Supported Languages (9 Languages)
- **English (`en`)** - `eng_Latn`
- **Tamil (`ta`)** - தமிழ் (`tam_Taml`)
- **Hindi (`hi`)** - हिन्दी (`hin_Deva`)
- **Telugu (`te`)** - తెలుగు (`tel_Telu`)
- **Malayalam (`ml`)** - മലയാളം (`mal_Mlym`)
- **Kannada (`kn`)** - ಕನ್ನಡ (`kan_Knda`)
- **French (`fr`)** - Français (`fra_Latn`)
- **Spanish (`es`)** - Español (`spa_Latn`)
- **German (`de`)** - Deutsch (`deu_Latn`)

### Core Features & Architecture
- **Language Detection:** Regex and Unicode block ranges for Indic scripts (Tamil, Devanagari, Telugu, Malayalam, Kannada) and Latin stopword/diacritic classifiers for French, German, and Spanish.
- **Translation Pipelines:**
  - Primary: NLLB-200 (`facebook/nllb-200-distilled-600M`) / MarianMT with FLORES-200 script codes.
  - Fast/Online: `deep-translator` adapter using `MyMemoryTranslator` (`ta-IN`, `hi-IN`, `fr-FR`, etc.).
  - Deterministic Fallback: Academic glossary matching engine for offline and continuous test verification.
- **Smart Chunking & Formatting:** Sentence-boundary-aware chunker respecting paragraph transitions (`\n\n`) and bullet lists, reassembling text without duplicate overlap.
- **Translation Validation:** Validates output length ratio, numerical accuracy, and technical terminology retention.
- **Multi-Format Export:** Instant export of translated notes into UTF-8 `.txt` and Unicode `.pdf` (using system fonts like Arial / Nirmala).

### Authenticated Translation REST Endpoints
- `GET /api/translations/languages`: Lists all 9 supported languages with native names and script codes.
- `POST /api/translations/generate`: Translates a summary given `summary_id` and `target_language`.
- `GET /api/translations/<id>`: Retrieves a translated summary by ID.
- `GET /api/translations/history`: Lists paginated translation history for the current user.
- `DELETE /api/translations/<id>`: Deletes a translation record.
- `GET /api/translations/<id>/export?format=pdf|txt`: Downloads translated notes in PDF or plain text format.

---

## 16. Phase 9: Personalized Learning Recommendations & Adaptive Learning Paths

Phase 9 introduces an explainable, data-grounded educational intelligence layer that dynamically analyzes student performance across completed quiz attempts, detects knowledge deficits, recommends targeted learning activities, and generates sequential adaptive learning pathways.

### Core Architecture & Flow
1. **Performance Aggregation:** Analyzes real `QuizAttempt` and `QuizResponse` records, grouping questions by conceptual topics.
2. **Deterministic Topic Mapping:** Questions are mapped to topics via Summary definition terms and extracted keywords first, followed by sanitized Document titles, and source reference metadata.
3. **Deficit & Strength Classification:** Configurable boundary thresholds classify each topic into mastery levels:
   - **Insufficient Data:** `< 3` attempts recorded.
   - **Needs Improvement (Weak):** Accuracy `< 50%`.
   - **Developing (Moderate):** Accuracy `50%` to `< 70%`.
   - **Good:** Accuracy `70%` to `< 85%`.
   - **Strong:** Accuracy `≥ 85%`.
4. **Adaptive Difficulty Engine:** Recommends optimal quiz difficulty tiers (`easy`, `medium`, `hard`) based on topic proficiency and historical volume without enforcing rigid locks.
5. **Explainable Recommendations:** Synthesizes actionable study recommendations with transparent reasons grounded in specific attempt counts and accuracy metrics:
   - High Priority: Targeted revision of weak topics (`retry_weak_topic`) and declining retention (`revisit_document`).
   - Medium Priority: Terminology and definitions revision (`review_definitions`) and baseline calibration (`insufficient_data`).
   - Low Priority / Enrichment: Advanced analytical challenge quizzes (`advanced_quiz`) for strong topics.
6. **Adaptive Learning Paths (4 Milestones):**
   - Stage 1: Conceptual Summary Ingestion (`summary_review`)
   - Stage 2: Key Takeaways Study (`takeaways_study`)
   - Stage 3: Technical Definitions & Terminology Drill (`definitions_review`)
   - Stage 4: Adaptive Practice Assessment (`quiz_practice`)
   *Server-Side Verification:* Activity milestones verify actual study resource accessibility and completed quiz attempts before marking progress done.

### Authenticated Phase 9 REST Endpoints
- `GET /api/learning/overview`: Holistic learning KPIs, strong/weak topic lists, and recommended next action.
- `GET /api/learning/topics`: Topic-level metrics, accuracy, question breakdown, and longitudinal trends.
- `GET /api/learning/adaptive-difficulty`: Data-grounded quiz difficulty tier recommendation.
- `GET /api/recommendations`: Paginated recommendations filtered by `status` and `priority`.
- `POST /api/recommendations/generate`: Triggers recommendation engine to synthesize new items.
- `PATCH /api/recommendations/<id>`: Updates recommendation status (`pending`, `in_progress`, `completed`, `dismissed`).
- `POST /api/learning-paths/generate`: Creates an adaptive 4-stage sequential learning path.
- `GET /api/learning-paths`: Lists user learning paths with progress percentages and milestone statuses.
- `GET /api/learning-paths/<id>`: Retrieves full path details and ordered milestone activities.
- `PATCH /api/learning-paths/<id>`: Updates path state (`not_started`, `in_progress`, `paused`, `completed`).
- `POST /api/learning-paths/<id>/activities/<activity_id>/complete`: Verifies and marks a milestone completed, updating path progress.
- `DELETE /api/learning-paths/<id>`: Safely deletes learning path and cascaded milestones.

### Methodology Note: Rule-Based Explainability vs Black-Box ML
In accordance with educational SaaS best practices, Phase 9 utilizes deterministic, transparent rule-based statistical algorithms and threshold classification rather than unexplainable black-box machine learning models. Every recommendation provides students and instructors with direct, verifiable evidence (e.g., exact attempts, accuracy percentages, and active milestones).

---

## 17. Docker Deployment Instructions

To build and run the entire application using Docker Compose:

```bash
docker compose up --build -d
```

Check running container logs:
```bash
docker compose logs -f backend
```

Stop containers:
```bash
docker compose down
```

---

## 18. Common Troubleshooting Steps

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `API: Offline` on landing page | Flask server not started or port blocked | Start `python backend/run.py` and confirm `http://127.0.0.1:5000/api/health` responds. |
| `CORS Error` in browser console | Origin not permitted in config | Ensure `CORS_ORIGINS=*` is set in `.env` for local testing. |
| `No module named 'backend'` | Path execution mismatch | Run using `python backend/run.py` from repository root. `run.py` automatically injects paths into `sys.path`. |
| Port 5000 in use | Another application using port 5000 | Change `PORT=5001` in `.env` and update `frontend/js/config.js`. |

