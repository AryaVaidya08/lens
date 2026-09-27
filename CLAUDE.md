# HCP Spatial Copilot — project context

Read this before touching code. It's the shared context every lane's coding agent needs so four people can work in this repo at once without stepping on each other or re-litigating decisions that are already made.

## What this is

A hackathon project (GTHacks — Impiricus's "Invent the Next Way We Engage HCPs" challenge, and the Lighthouse Immersive track) that has grown past its original scaffold into three connected pieces: an iOS app, a FastAPI + MongoDB backend, and a React web dashboard. A physician points their phone at a drug sample. A trained Core ML detector finds the bottle in frame, a barcode scan is tried first with on-device OCR as fallback, and the app shows a personalized AR heads-up display, then answers follow-up voice questions via a RAG + LLM pipeline. The web dashboard gives a clinician the same account, chat history, and drug lookup from a browser.

**The pitch, in one line:** most pharma engagement is push (a message that gets ignored) or pull (a physician has to decide to search). This app makes *picking the object up* the trigger — no search intent required. That's the differentiator, and it's why the demo has to show the personalization loop clearly, not just "camera + chatbot."

**The personalization loop (the single most important thing to get right):** each HCP has an engagement history per drug. That history determines a familiarity tier (`new` / `returning` / `expert`), which changes what the HUD leads with and what retrieval prioritizes. Every scan updates that history. The same HCP scanning the same drug twice must visibly get a different, more advanced answer the second time. On top of tier, the HCP's registered specialty reshapes which dossier sections get surfaced (`app/personalization/scorer.py`'s specialty lens). If you're touching `personalization/scorer.py`, `routes/drug.py`, or `routes/engagement.py`, keep this loop in mind — it's the whole point.

Full narrative context: `SCAFFOLD_HANDOFF.md` (the original planning doc this scaffold was generated from — it describes the pre-auth, pre-MongoDB, SQLite-based starting point, not the current state).

## Explicit scope decisions

Two of the original scope decisions below have already been deliberately reversed because the demo needed them — that's not scope creep, don't revert them. The rest still hold; don't add them back in even if it seems like an obvious best practice:

- **Real authentication now exists** and replaces the original persona-picker plan: register/login/logout, hashed passwords, bearer session tokens, rate limiting on auth endpoints, and a recovery-code-based password reset (`app/routes/auth.py`, `app/db/{passwords,sessions,resets,accounts}.py`). The backend no longer trusts a client-supplied `hcp_id` for anything auth-sensitive — routes are scoped to the authenticated session. Don't reintroduce a "just trust the hcp_id the app sends" shortcut.
- **Real MongoDB now backs everything** (Atlas or local, `mongomock` in-memory for tests) and replaces the original SQLite plan (`app/db/database.py`, `app/db/mongo.py`). Don't reintroduce SQLite/SQLAlchemy.
- **No patient-level personalization of the familiarity tier.** Tier scoring (`new`/`returning`/`expert`) stays HCP-level only. The one exception: `POST /drug/{id}/ask` and `GET /drug/{id}/summary` accept an optional `patient_id` — when the HCP has a patient selected for the scan, that patient's age/sex/weight/allergies/current medications are passed to the LLM as plain context (threaded through `app/llm/client.py::generate_answer`'s `patient_context` param) so voice follow-up questions can be answered with that patient in mind. This does not change retrieval, tier scoring, or the HUD's chart-check flags (`personalization/patient_check.py`, a name-based allergy/medication overlap check — explicitly not a clinical decision), which remain separate.
- **No cloud storage bucket.** Drug reference docs (~1,800 openFDA-derived dossiers) are plain files in `backend/data/drug_docs/`, read by `retrieval/ingest.py` at startup.
- **No hosted vector database.** Retrieval is an in-memory index rebuilt at startup, embedded with `sentence-transformers`, accessed only through `retrieval/index.py::retrieve()`.
- **No message queues, no microservices, no container orchestration.** One FastAPI service, one MongoDB deployment, one iOS app, one web frontend.

See `docs/architecture.md` for how each of the still-true items upgrades later, and why now is not that time.

## The two swap points — never bypass these

- `backend/app/retrieval/index.py::retrieve(drug_id, query, top_k=None, specialty=None)` is the *only* way anything calls retrieval. No file outside `retrieval/` should import embeddings or a vector store directly.
- `backend/app/llm/client.py::generate_answer(query, context, tier="new", specialty=None, patient_context=None)` is the *only* way anything calls the LLM. No other file should call the LLM API directly.

Both exist so the swap described in `docs/architecture.md` (hosted vector DB, different LLM provider) never touches a caller.

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
  app/personalization/       Familiarity tier + specialty-lens scoring, patient-chart checks
  app/llm/                   LLM client wrapper (xAI Grok + extractive fallback)
  app/detection/             Barcode/OCR-to-drug resolution catalog
  data/drug_docs/            ~1,800 openFDA-derived drug reference docs, ingested at startup
  tests/                     pytest suite (auth, patients, scoring, ingestion, retrieval, e2e flows)
frontend/                React + Vite clinician web dashboard, hits the same backend API
PillBottleDetector.mlproj/  Create ML project for the trained bottle-detection model
training/                Notes + data for retraining PillBottleDetector
docs/                    architecture.md (scaling path) + team-context/ (per-lane docs)
```

Most files here are filled in now, not stubs — this layout is still the reason four people can edit in parallel without merge conflicts, so keep new work inside the existing single-responsibility boundaries rather than redesigning the tree.

## API contract (the thing that couples the two halves)

The full, current endpoint list (all ~23 routes, with auth requirements) lives in `README.md`'s "API contract" section — that's the source of truth, not this file, so it doesn't drift into two different stale copies. If you change a request/response shape, update it in the same change everywhere it's described: `backend/app/routes/*.py`, `README.md`, `Lens/Lens/Networking/Endpoints.swift` + `Lens/Lens/Models/*.swift`, and `frontend/src/api.js`.

## Team lanes

Each lane has a dedicated context doc — read yours, and paste it into your own agent's context if you're working in a fresh session. These have been refreshed against the current MongoDB/real-auth/frontend state, same as this file and `docs/architecture.md`.

- [`docs/team-context/ar-detection.md`](docs/team-context/ar-detection.md) — camera, ARKit, on-device barcode/OCR
- [`docs/team-context/backend-data.md`](docs/team-context/backend-data.md) — FastAPI, MongoDB schema, retrieval ingestion mechanics
- [`docs/team-context/voice-llm.md`](docs/team-context/voice-llm.md) — speech I/O, RAG retrieval weighting, LLM integration
- [`docs/team-context/content-demo.md`](docs/team-context/content-demo.md) — drug dossiers, personalization tuning, demo script

See [`training/README.md`](training/README.md) for retraining the Core ML bottle detector (`PillBottleDetector.mlproj/`) that now runs ahead of barcode/OCR in `ObjectDetector.swift`.

## Running things

Everything runs locally on a laptop for now — no containers, no deployment. There is no `Dockerfile`; don't add one back without asking.

- **Backend:** `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` (from inside `backend/`, so `app.main` resolves). `GET /health` should return `{"status": "ok"}`; `GET /status` reports which backends are actually active (real embeddings vs. lexical fallback, LLM vs. offline fallback, which MongoDB it's talking to) — check both after setup. Configure `MONGODB_URI` and `XAI_API_KEY` in `backend/.env` (see `app/config.py` for every env var it reads).
- **iOS:** open `Lens/Lens.xcodeproj` in Xcode and run on a physical device — ARKit and the camera don't work in the simulator. Point `Networking/APIClient.swift`'s base URL at your laptop's local network IP (not `localhost`), since a physical device can't reach the laptop's loopback address. The project uses Xcode 16's file-system-synchronized groups, so any file you add under `Lens/Lens/` shows up automatically — no `.pbxproj` editing needed.
- **Web dashboard:** `cd frontend && npm install && npm run dev`, runs on `http://localhost:5173` (the backend's CORS config expects this origin).
- **Tests:** `cd backend && pytest` runs the full suite in `backend/tests/` (~25 files covering auth, patients, scoring, ingestion, retrieval, and end-to-end flows).

## Working conventions

- Follow the existing single-responsibility file layout when adding new code; don't redesign it without telling the other lanes — the layout is what lets four people edit in parallel.
- This is a hackathon: prioritize a working, demoable path over polish, generality, or error handling for cases that won't come up in the demo.
- Don't touch another lane's files unless you've coordinated — the API contract and the swap-point functions are the only things every lane needs to agree on.
