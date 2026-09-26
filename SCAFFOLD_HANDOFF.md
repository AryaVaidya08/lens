# Repo scaffolding handoff

## Your task, precisely

Create the directory and file structure below **only**. Every file must exist and contain a stub: a header comment/docstring describing its responsibility, and function/class signatures where the design calls for them with `# TODO: implement` (Python) or `// TODO: implement` (Swift) bodies.

**Do not implement any real logic.** No working ARKit rendering, no real detection, no real retrieval, no real personalization scoring, no real LLM calls, no real database queries. The goal is a directory of stub files with clear responsibilities, so four people can start editing different files immediately with zero merge conflicts on file creation.

The one exception: write the actual, full README.md content given at the bottom of this document, and the actual `docs/architecture.md` content given at the bottom — those are real documentation, not code stubs.

---

## Project context (for your own understanding, and to draw on for the README)

**Working name:** HCP Spatial Copilot

**What it is:** An iOS app for a hackathon (GTHacks, targeting Impiricus's "Invent the Next Way We Engage HCPs" sponsor challenge, and the Lighthouse Immersive track). A physician points their phone at a drug sample or package. The app recognizes it on-device (barcode/OCR, or a small on-device classifier as backup) and shows a personalized AR heads-up display with relevant info, anchored in space via ARKit. The physician can then ask follow-up questions by voice; a RAG pipeline retrieves grounded context about that drug and an LLM generates a spoken answer.

**The core insight the whole pitch rests on:** most pharma engagement platforms (including Impiricus's real products) are either push-based (a message sent to a physician) or pull-based (a physician has to decide to go search for something). A physical drug sample that's dropped off in an office and never gets a follow-up search represents dead, paid-for engagement. This app turns *picking the object up* into the trigger — no search intent required from the physician. That's the differentiator: not "faster lookup than typing," but "captures engagement that currently doesn't happen at all."

**Personalization loop:** each HCP has an engagement history (how many times they've encountered this drug through the app before). That history determines a "familiarity tier," which changes both what the HUD leads with (basics vs. dosing/trial data) and what the RAG retrieval prioritizes when answering follow-up questions. Every interaction updates that history, so the same HCP scanning the same drug a second time visibly gets a different, more advanced answer. This closed loop is the single most important thing to demo clearly — it's what makes this look like a real engagement engine rather than a lookup app with a camera.

**Explicit scope decisions already made — do not add these:**
- No real authentication. A simple in-app picker lets the demo user select one of a few preset HCP personas (name + specialty). The backend trusts whatever `hcp_id` the app sends.
- No Firebase, no external auth or database service. Everything runs through the FastAPI backend and a local SQLite database.
- No patient-level personalization — only HCP-level.
- No cloud storage bucket. Drug reference documents live in a plain folder in the repo (`backend/data/drug_docs/`) and are read by an ingestion script at backend startup.
- No hosted vector database. The retrieval index is in-memory, rebuilt from the docs folder at startup, and sits behind one function (`retrieve()`) so it can be swapped for something more scalable later without touching any other code.
- No message queues, no microservices split, no container orchestration. One FastAPI service, one SQLite file, one iOS app.

---

## Full directory tree to create

```
hcp-spatial-copilot/
├── README.md
├── .gitignore
│
├── ios/
│   └── Lens/
│       ├── App/
│       │   ├── HCPCopilotApp.swift
│       │   └── AppState.swift
│       ├── Detection/
│       │   ├── BarcodeScanner.swift
│       │   └── TextRecognizer.swift
│       ├── AR/
│       │   ├── ARSessionManager.swift
│       │   └── HUDOverlayView.swift
│       ├── Voice/
│       │   ├── SpeechRecognizer.swift
│       │   └── SpeechSynthesizer.swift
│       ├── Networking/
│       │   ├── APIClient.swift
│       │   └── Endpoints.swift
│       ├── Models/
│       │   ├── HCP.swift
│       │   ├── Drug.swift
│       │   └── DrugSummary.swift
│       └── Views/
│           ├── PersonaPickerView.swift
│           ├── CameraView.swift
│           └── HUDView.swift
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── profile.py
│   │   │   ├── detect.py
│   │   │   ├── drug.py
│   │   │   └── engagement.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── database.py
│   │   │   └── seed.py
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── index.py
│   │   │   ├── embed.py
│   │   │   └── ingest.py
│   │   ├── personalization/
│   │   │   ├── __init__.py
│   │   │   └── scorer.py
│   │   └── llm/
│   │       ├── __init__.py
│   │       └── client.py
│   ├── data/
│   │   └── drug_docs/
│   │       └── .gitkeep
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_health.py
│
└── docs/
    └── architecture.md
```

---

## Backend stub content, file by file

**`app/main.py`** — FastAPI app instance, includes all four routers, a `GET /health` endpoint that returns `{"status": "ok"}` (this one should actually work, not be a stub — it's needed to verify deployment early).

**`app/config.py`** — placeholder for env-based settings (LLM API key, DB path). Stub a `Settings` class/object.

**`routes/profile.py`** — `GET /profile/{hcp_id}` → stub function `get_profile(hcp_id: str)`. Docstring: returns HCP specialty and familiarity tier per drug.

**`routes/detect.py`** — `POST /detect` → stub function `detect_drug(payload)`. Docstring: takes a decoded barcode string or OCR text, returns `{drug_id, name}`.

**`routes/drug.py`** — two routes: `GET /drug/{drug_id}/summary?hcp_id=...` (stub `get_summary`) and `POST /drug/{drug_id}/ask` (stub `ask_question`, body `{hcp_id, query}`, returns `{answer_text}`).

**`routes/engagement.py`** — `POST /engagement/log`, body `{hcp_id, drug_id}` → stub `log_engagement`. Docstring: increments touch count.

**`db/models.py`** — SQLAlchemy models, fields only, no methods: `HCP(id, name, specialty)`, `Drug(id, name, barcode)`, `Engagement(hcp_id, drug_id, touch_count, last_seen)`.

**`db/database.py`** — SQLite engine + session setup stub (`get_db()` dependency function signature).

**`db/seed.py`** — stub `seed()` function. Docstring: populates 3–4 mock HCPs and a handful of mock drugs before the demo, so personalization has real starting state.

**`retrieval/index.py`** — the swap point. Stub: `def retrieve(drug_id: str, query: str) -> list[str]:`. Docstring must state explicitly: "This is the single interface between the rest of the app and however retrieval is implemented. Do not let any other file call embeddings or a vector store directly — always go through this function, so it can be replaced with a hosted vector DB later without touching callers."

**`retrieval/embed.py`** — stub `def embed_text(text: str) -> list[float]:`.

**`retrieval/ingest.py`** — stub `def ingest_docs(folder_path: str):`. Docstring: reads all files in `data/drug_docs/`, chunks and embeds them, builds the in-memory index used by `index.py`.

**`personalization/scorer.py`** — the product logic. Stub `def score_familiarity(hcp_id: str, drug_id: str) -> str:`, returning one of `"new"`, `"returning"`, `"expert"`. Docstring should note this is the file most likely to get walked through live in the demo/pitch, so keep it short and readable even as a stub.

**`llm/client.py`** — the other swap point. Stub `def generate_answer(query: str, context: list[str]) -> str:`. Docstring: wraps whichever LLM API is used; nothing else in the codebase should call the LLM API directly.

**`requirements.txt`** — list expected packages (don't pin versions yet): `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `sentence-transformers`, `numpy`, `requests`, `python-multipart`.

**`Dockerfile`** — standard minimal FastAPI/uvicorn Dockerfile skeleton, Python 3.11 slim base.

**`tests/test_health.py`** — one real test hitting `/health`, since it's the one real endpoint.

---

## iOS stub content, file by file

**`App/HCPCopilotApp.swift`** — `@main` SwiftUI `App` struct, launches `PersonaPickerView`.

**`App/AppState.swift`** — `ObservableObject` stub holding `selectedHCP`, `currentDrug`, `familiarityTier` as `@Published` properties.

**`Detection/BarcodeScanner.swift`** — class stub wrapping `VNDetectBarcodesRequest`, one method signature `func scan(pixelBuffer:) -> String?`.

**`Detection/TextRecognizer.swift`** — class stub wrapping `VNRecognizeTextRequest`, same shape.

**`AR/ARSessionManager.swift`** — stub managing `ARSession`/`ARSCNView` setup, method signature `func placeAnchor(for result: DetectionResult)`.

**`AR/HUDOverlayView.swift`** — SwiftUI `View` stub rendering the info card; takes a `DrugSummary` as input.

**`Voice/SpeechRecognizer.swift`** — stub wrapping `SFSpeechRecognizer`, method `func startListening(completion: (String) -> Void)`.

**`Voice/SpeechSynthesizer.swift`** — stub wrapping `AVSpeechSynthesizer`, method `func speak(_ text: String)`.

**`Networking/APIClient.swift`** — stub with one method per backend endpoint, matching the contract exactly: `getProfile`, `detectDrug`, `getSummary`, `askQuestion`, `logEngagement`. Return types should reference the `Models/` structs.

**`Networking/Endpoints.swift`** — a `enum Endpoints` or `struct` listing all five paths as constants, so the whole contract is visible in one file.

**`Models/HCP.swift`**, **`Models/Drug.swift`**, **`Models/DrugSummary.swift`** — `Codable` structs matching the backend's response shapes.

**`Views/PersonaPickerView.swift`** — SwiftUI View stub, a list of preset HCP names to tap; sets `AppState.selectedHCP`.

**`Views/CameraView.swift`** — SwiftUI View stub hosting the camera feed + AR overlay.

**`Views/HUDView.swift`** — SwiftUI View stub for the on-screen (non-AR-anchored) fallback display of the same info.

---

## `.gitignore`

Standard Xcode + Python: `.DS_Store`, `xcuserdata/`, `*.xcworkspace`, `__pycache__/`, `*.pyc`, `.env`, `*.db`.

---

## README.md — write this exact content at the repo root

```markdown
# HCP Spatial Copilot

An iOS app that turns picking up a drug sample into an engagement event — not a faster search, a different trigger entirely. Built for GTHacks, targeting Impiricus's "Invent the Next Way We Engage HCPs" challenge and the Lighthouse Immersive track.

## The idea

Most pharma engagement today is either pushed at a physician (a message they may ignore) or requires them to decide to go search for something. A physical sample dropped off in an office and never followed up on is paid-for engagement that just dies. This app removes the search step: point your phone at a drug package, and an AR heads-up display shows personalized info instantly, anchored in space. Ask a follow-up question by voice and get a grounded, spoken answer.

The personalization is the point, not a feature on top: each HCP's engagement history with a given drug determines whether the HUD leads with basics or skips straight to dosing and trial data — and every interaction updates that history, so the same physician scanning the same drug a second time gets a visibly different, more advanced answer.

## Tech stack

- **iOS app:** Swift/SwiftUI, ARKit, Vision (barcode/OCR detection), Speech + AVSpeechSynthesizer
- **Backend:** FastAPI, SQLAlchemy + SQLite, an in-memory RAG retrieval layer, a wrapper around the hackathon sponsor's LLM API
- **Drug reference docs:** plain files in `backend/data/drug_docs/`, ingested at backend startup
- No authentication (persona picker instead), no Firebase, no cloud storage bucket — deliberately, to match the 36-hour build window. See `docs/architecture.md` for how each of these upgrades later.

## API contract

| Endpoint | Purpose |
|---|---|
| `GET /profile/{hcp_id}` | Returns specialty + familiarity tier per drug |
| `POST /detect` | Barcode/OCR result → `{drug_id, name}` |
| `GET /drug/{drug_id}/summary?hcp_id=` | Personalized HUD content |
| `POST /drug/{drug_id}/ask` | RAG + LLM follow-up answer |
| `POST /engagement/log` | Increments touch count |

## Repo layout

See the tree in this repo — `ios/` and `backend/` are independent; the API contract above is the only thing that couples them. Build against the contract, not against each other's code.

## Team lanes

- **AR & detection** — camera, ARKit, on-device barcode/OCR
- **Backend & data** — FastAPI, SQLite schema, retrieval ingestion
- **Voice & LLM** — speech I/O, RAG retrieval weighting, LLM integration
- **Content & demo** — mock drug dossiers, personalization tuning, demo script

## Setup

_Fill in once dependencies are installed — `backend/requirements.txt` for the API, standard Xcode project for `ios/`._
```

---

## `docs/architecture.md` — write this exact content

```markdown
# Scaling path

This is built deliberately small for a 36-hour demo, with specific upgrade points already designed in — not guessed at. Nothing below requires a rewrite; each row upgrades what sits behind an existing interface.

| Component | Tonight | Move when... | Next step |
|---|---|---|---|
| Drug docs | Repo folder | A non-engineer needs to add a dossier without a code deploy | Cloud Storage bucket (GCS or R2) |
| HCP/engagement data | SQLite file | More than one backend instance runs concurrently | Managed Postgres (Cloud SQL, RDS, Supabase) |
| Retrieval index | In-memory, rebuilt at startup | Startup time grows, or need to scale past one machine | Persisted FAISS index, then a managed vector DB (pgvector) |
| LLM | Sponsor's API | Cost/rate limits, or sponsor relationship ends | Own API key + response caching |
| "Auth" | Persona picker | Can't let anyone claim to be any physician anymore | Sign in with Apple, or NPI-verified login |
| Deployment | Single Cloud Run/Render instance | Traffic exceeds one instance | Auto-scaling (no code change needed) |

The pattern: `retrieve()` and the LLM client are each called from exactly one place in the codebase. Whatever is upgraded, callers never change.
```
