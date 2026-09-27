# HCP Spatial Copilot

An iOS app that turns picking up a drug sample into an engagement event — not a faster search, a different trigger entirely. Built for GTHacks, targeting Impiricus's "Invent the Next Way We Engage HCPs" challenge and the Lighthouse Immersive track.

## The idea

Most pharma engagement today is either pushed at a physician (a message they may ignore) or requires them to decide to go search for something. A physical sample dropped off in an office and never followed up on is paid-for engagement that just dies. This app removes the search step: point your phone at a drug package, and an AR heads-up display shows personalized info instantly. Ask a follow-up question by voice and get a grounded, spoken answer.

The personalization is the point, not a feature on top: each HCP's engagement history with a given drug determines whether the HUD leads with basics or skips straight to dosing and trial data — and every interaction updates that history, so the same physician scanning the same drug a second time gets a visibly different, more advanced answer. On top of familiarity tier, the specialty a clinician registers with also reshapes which dossier sections get surfaced (cardiology gets led into interactions/pharmacology, pediatrics into pediatric-use sections, etc.).

This has grown past the original 36-hour scaffold into three connected pieces: an iOS app, a FastAPI backend, and a React web dashboard.

## What's actually built

**iOS app** (`Lens/`)
- Detection pipeline: a trained Core ML object detector (`PillBottleDetector`, see `PillBottleDetector.mlproj/` and `training/`) finds the bottle in frame, then a barcode scan is tried first, with on-device OCR (Vision) as the fallback — restricted to the region the detector found.
- ARKit-backed camera passthrough with a 2D screen-tracked HUD bubble (not a 3D-anchored node — see the design note in `ARSessionManager.swift` for why) that follows the detected object and includes recovery from ARSession interruptions/failures.
- Voice assistant: on-device speech recognition + spoken replies (AVSpeechSynthesizer), wired to `POST /drug/{id}/ask`.
- Real clinician accounts: register, login/logout, change password, forgot/reset password via a recovery code — not a persona picker.
- Patient charts: list, create, view; "use for scan" attaches the selected patient's context (age/sex/weight/allergies/meds) to a scan and to voice follow-up questions.
- Medication reviews: scan a reference medication list and confirmed bottles via `VNDocumentCameraViewController` + OCR, then get a literal (non-diagnostic) comparison — mismatched strength/formulation/directions, unmatched bottles, patient-reported use — with a shareable follow-up report.
- Scan/chat history synced from MongoDB, pull-to-refresh.
- Settings + profile editing.

**Backend** (`backend/`)
- FastAPI + **MongoDB** (Atlas or local; `mongomock` in-memory for tests) — this replaced the original SQLite plan.
- Real auth: hashed passwords, bearer session tokens, per-key rate limiting on auth endpoints, and a recovery-code-based password reset flow (`app/db/passwords.py`, `sessions.py`, `resets.py`).
- RAG retrieval over ~1,800 openFDA-derived drug dossiers (`backend/data/drug_docs/`), chunked and embedded with `sentence-transformers`, ranked by cosine similarity plus section-name and specialty-lens bonuses (`app/retrieval/index.py::retrieve`, the one retrieval swap point).
- LLM answers via xAI's Grok API (`app/llm/client.py::generate_answer`, the one LLM swap point), with a grounded extractive fallback when no API key is configured so the demo never goes fully dark.
- Personalization: familiarity tier (`new` / `returning` / `expert`) per HCP+drug from engagement counts, plus a specialty-to-dossier-section lens covering ~80 raw specialty labels mapped onto ~19 clinical groupings (`app/personalization/scorer.py`).
- Patient-chart safety flags: name-based overlap between a patient's allergies/current meds and the scanned drug's dossier terms — explicitly a name match, not a clinical decision (`app/personalization/patient_check.py`).
- Medication-review comparison logic and report generation (`app/routes/medication_reviews.py`).
- A real test suite (`backend/tests/`, ~25 files) covering auth, patients, scoring, ingestion, retrieval, and end-to-end flows — not just `test_health.py`.

**Web dashboard** (`frontend/`)
- React 19 + Vite app for a clinician to work from a browser instead of the iOS app: login (same account/session backend), a dashboard, chat history (view/rename/delete conversations), a drug lookup + Q&A view, and patient management.
- Talks to the exact same backend and API contract as the iOS app.

## Tech stack

- **iOS app:** Swift/SwiftUI, ARKit, Vision (Core ML object detection + barcode/OCR), VisionKit document scanning, Speech + AVSpeechSynthesizer
- **Backend:** FastAPI, PyMongo (MongoDB/Atlas, `mongomock` for tests), `sentence-transformers` for embeddings, xAI Grok for LLM answers
- **Web dashboard:** React 19, Vite
- **Drug reference docs:** ~1,800 openFDA-derived plain-text dossiers in `backend/data/drug_docs/`, ingested and embedded at backend startup
- No cloud storage bucket, no message queues/microservices/containers — still true to the hackathon build. See `docs/architecture.md` for the scaling path (note: that doc and `CLAUDE.md`'s scope-decisions section still describe the original SQLite/persona-picker plan and are due for a refresh against what's above).

## API contract

All endpoints below except `register`/`login`/`forgot-password`/`reset-password` require a session bearer token (`Authorization: Bearer <token>`, issued at register/login) and are scoped to the authenticated HCP.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Create a clinician account |
| `POST` | `/auth/login` | Email + password → session token |
| `POST` | `/auth/logout` | Revoke the current session |
| `POST` | `/auth/change-password` | Change password while signed in |
| `POST` | `/auth/forgot-password` | Verify recovery code, start a reset ticket |
| `POST` | `/auth/reset-password` | Complete a reset with a fresh password |
| `GET` | `/profile/{hcp_id}` | HCP profile + specialty |
| `PATCH` | `/profile/{hcp_id}` | Update profile fields |
| `GET` | `/profile/{hcp_id}/chats` | List saved voice/chat conversations |
| `PATCH` | `/profile/{hcp_id}/chats/{conversation_id}` | Rename a conversation |
| `DELETE` | `/profile/{hcp_id}/chats/{conversation_id}` | Delete a conversation |
| `GET` | `/profile/{hcp_id}/patients` | List this HCP's patient charts |
| `POST` | `/profile/{hcp_id}/patients` | Create a patient chart |
| `GET` | `/profile/{hcp_id}/patients/{patient_id}` | Get one patient chart |
| `GET` | `/patients/{patient_id}/medication-reviews` | List medication reviews for a patient |
| `PUT` | `/patients/{patient_id}/medication-reviews/{review_id}` | Save/update a medication review (optimistic concurrency via `revision`) |
| `POST` | `/detect` | Barcode/OCR text → `{drug_id, name}` |
| `GET` | `/drug/search` | Name search over the full drug catalog |
| `GET` | `/drug/{drug_id}/summary?hcp_id=&patient_id=` | Personalized HUD content, optionally with a patient chart check |
| `POST` | `/drug/{drug_id}/ask` | RAG + LLM follow-up answer, optionally patient-aware |
| `POST` | `/engagement/log` | Increments touch count for an (hcp, drug) pair |
| `GET` | `/health` | Liveness check |
| `GET` | `/status` | Retrieval/embedding/LLM/DB backend status |

If you change a request/response shape, update it on both sides in the same change: `backend/app/routes/*.py` and `Lens/Lens/Networking/Endpoints.swift` + `Lens/Lens/Models/*.swift` (and `frontend/src/api.js` if the web dashboard uses it too).

## The two swap points — never bypass these

- `backend/app/retrieval/index.py::retrieve(drug_id, query, specialty=...)` is the *only* way anything calls retrieval.
- `backend/app/llm/client.py::generate_answer(query, context, tier, specialty=..., patient_context=...)` is the *only* way anything calls the LLM.

## Repo layout

```
Lens/                    iOS app (Xcode project — Lens/Lens.xcodeproj). Source lives in Lens/Lens/.
  Lens/App/                  App entry point + shared AppState
  Lens/Detection/            Core ML object detection, barcode/OCR, document scanning
  Lens/AR/                   ARKit session + spatial HUD + session lifecycle/recovery
  Lens/Voice/                Speech I/O + voice assistant session
  Lens/Networking/           API client + endpoint contract
  Lens/Models/               Codable structs matching backend responses
  Lens/Views/                SwiftUI screens (auth, patients, medication reviews, history, settings, voice)
backend/                 FastAPI service
  app/routes/                auth, profile, medication_reviews, detect, drug, engagement
  app/db/                    Mongo client, accounts, passwords, sessions, resets, seed data
  app/retrieval/             In-memory RAG (ingest, embed, index/retrieve)
  app/personalization/       Familiarity tier scoring + patient-chart checks
  app/llm/                   LLM client wrapper (xAI Grok + extractive fallback)
  app/detection/             Barcode/OCR-to-drug resolution catalog
  data/drug_docs/            ~1,800 openFDA-derived drug reference docs, ingested at startup
  tests/                     pytest suite
frontend/                React + Vite clinician web dashboard, hits the same backend API
PillBottleDetector.mlproj/  Create ML project for the trained bottle-detection model
training/                 Notes + data for retraining PillBottleDetector
docs/                    architecture.md (scaling path) + team-context/ (per-lane docs)
```

## Setup

Everything runs locally — no containers, no deployment.

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Verify it's up: `curl http://localhost:8000/health` should return `{"status": "ok"}`. Check `curl http://localhost:8000/status` to confirm which backends are actually active (real embeddings vs. lexical fallback, LLM vs. offline fallback, which MongoDB it's talking to). Configure `MONGODB_URI` (defaults to `mongodb://127.0.0.1:27017`, use a `mongomock://` URI or an Atlas connection string) and `XAI_API_KEY` in `backend/.env` — see `app/config.py` for every env var it reads.

**iOS:** open `Lens/Lens.xcodeproj` in Xcode and run on a physical device (ARKit and the camera don't work in the simulator). Point `Lens/Lens/Networking/APIClient.swift`'s base URL at your laptop's local IP (not `localhost`) so a physical device can reach the backend over the same Wi-Fi network.

**Web dashboard:**

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` by default (the backend's CORS config expects this origin) and talks to the same backend as the iOS app.

**Tests:** `cd backend && pytest`.

## Team lanes

Each lane has a dedicated context doc in `docs/team-context/` — read yours before you start, and hand it to your coding agent as context. `CLAUDE.md` at the repo root covers the project-wide rules every lane shares.

- **AR & detection** — camera, ARKit, on-device barcode/OCR/document scanning, the Core ML bottle detector
- **Backend & data** — FastAPI, MongoDB schema, auth, retrieval ingestion
- **Voice & LLM** — speech I/O, RAG retrieval weighting, LLM integration
- **Content & demo** — drug dossiers, personalization tuning, demo script
