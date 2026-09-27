# HCP Spatial Copilot — project context

Read this before touching code. It's the shared context every lane's coding agent needs so four people can work in this repo at once without stepping on each other or re-litigating decisions that are already made.

## What this is

A hackathon iOS app (GTHacks — Impiricus's "Invent the Next Way We Engage HCPs" challenge, and the Lighthouse Immersive track). A physician points their phone at a drug sample. The app detects it on-device (barcode/OCR), shows a personalized AR heads-up display anchored in space via ARKit, and answers follow-up voice questions via a RAG + LLM pipeline.

**The pitch, in one line:** most pharma engagement is push (a message that gets ignored) or pull (a physician has to decide to search). This app makes *picking the object up* the trigger — no search intent required. That's the differentiator, and it's why the demo has to show the personalization loop clearly, not just "camera + chatbot."

**The personalization loop (the single most important thing to get right):** each HCP has an engagement history per drug. That history determines a familiarity tier (`new` / `returning` / `expert`), which changes what the HUD leads with and what retrieval prioritizes. Every scan updates that history. The same HCP scanning the same drug twice must visibly get a different, more advanced answer the second time. If you're touching `personalization/scorer.py`, `routes/drug.py`, or `routes/engagement.py`, keep this loop in mind — it's the whole point.

Full narrative context: `SCAFFOLD_HANDOFF.md` (the original planning doc this scaffold was generated from).

## Explicit scope decisions — do not add these

These were decided deliberately for a 36-hour build. Don't "improve" the architecture by adding them back in, even if it seems like an obvious best practice:

- **No real authentication.** A persona picker lets the demo user select a preset HCP. The backend trusts whatever `hcp_id` the app sends. No JWTs, no sessions.
- **No Firebase, no external auth/DB service.** Everything is FastAPI + one local SQLite file.
- **No patient-level personalization of the familiarity tier.** Tier scoring (`new`/`returning`/`expert`) stays HCP-level only. The one exception: `POST /drug/{id}/ask` accepts an optional `patient_id` — when the HCP has a patient selected for the scan, that patient's age/sex/weight/allergies/current medications are passed to the LLM as plain context (`app/routes/drug.py::_patient_context_block`, threaded through `app/llm/client.py::generate_answer`'s `patient_context` param) so voice follow-up questions can be answered with that patient in mind. This does not change retrieval, tier scoring, or the HUD's chart-check flags (`personalization/patient_check.py`), which remain separate.
- **No cloud storage bucket.** Drug reference docs are plain files in `backend/data/drug_docs/`, read by `retrieval/ingest.py` at startup.
- **No hosted vector database.** Retrieval is an in-memory index rebuilt at startup, accessed only through `retrieval/index.py::retrieve()`.
- **No message queues, no microservices, no container orchestration.** One FastAPI service, one SQLite file, one iOS app.

See `docs/architecture.md` for exactly how each of these upgrades later, and why now is not that time.

## The two swap points — never bypass these

- `backend/app/retrieval/index.py::retrieve(drug_id, query)` is the *only* way anything calls retrieval. No file outside `retrieval/` should import embeddings or a vector store directly.
- `backend/app/llm/client.py::generate_answer(query, context)` is the *only* way anything calls the LLM. No other file should call the LLM API directly.

Both exist so the swap described in `docs/architecture.md` (hosted vector DB, different LLM provider) never touches a caller.

## Repo layout

```
Lens/            iOS app (Xcode project — Lens/Lens.xcodeproj). Source lives in Lens/Lens/.
  Lens/App/          App entry point + shared AppState
  Lens/Detection/    Vision-based barcode/OCR
  Lens/AR/           ARKit session + spatial HUD
  Lens/Voice/        Speech I/O
  Lens/Networking/   API client + endpoint contract
  Lens/Models/       Codable structs matching backend responses
  Lens/Views/        SwiftUI screens
backend/         FastAPI service
  app/routes/        One file per resource (profile, detect, drug, engagement)
  app/db/            SQLAlchemy models + SQLite session
  app/retrieval/      In-memory RAG (ingest, embed, index/retrieve)
  app/personalization/  Familiarity tier scoring
  app/llm/            LLM client wrapper
  data/drug_docs/    Plain-text drug reference docs, ingested at startup
docs/            architecture.md (scaling path) + team-context/ (per-lane docs)
```

Everything is currently **stub files** — TODO markers, signatures, and docstrings only, no working logic yet. That's expected; the point of this scaffold is that every file already has a clear, single responsibility so lanes can fill theirs in without merge conflicts on file creation.

## API contract (the thing that couples the two halves)

| Endpoint | Purpose |
|---|---|
| `GET /profile/{hcp_id}` | HCP specialty + familiarity tier per drug |
| `POST /detect` | Barcode/OCR result → `{drug_id, name}` |
| `GET /drug/{drug_id}/summary?hcp_id=` | Personalized HUD content |
| `POST /drug/{drug_id}/ask` | RAG + LLM follow-up answer → `{answer_text}` |
| `POST /engagement/log` | Increments touch count |

If you change a request/response shape, update it on both sides in the same change: `backend/app/routes/*.py` and `Lens/Lens/Networking/Endpoints.swift` + `Lens/Lens/Models/*.swift`.

## Team lanes

Each lane has a dedicated context doc — read yours, and paste it into your own agent's context if you're working in a fresh session:

- [`docs/team-context/ar-detection.md`](docs/team-context/ar-detection.md) — camera, ARKit, on-device barcode/OCR
- [`docs/team-context/backend-data.md`](docs/team-context/backend-data.md) — FastAPI, SQLite schema, retrieval ingestion mechanics
- [`docs/team-context/voice-llm.md`](docs/team-context/voice-llm.md) — speech I/O, RAG retrieval weighting, LLM integration
- [`docs/team-context/content-demo.md`](docs/team-context/content-demo.md) — mock drug dossiers, personalization tuning, demo script

Once the actual demo drug bottles are settled, see [`training/README.md`](training/README.md) for training a Create ML image classifier on them — a real upgrade over the generic objectness detector in `ObjectDetector.swift`, for when barcode/OCR isn't reliable enough on its own.

## Running things

Everything runs locally on a laptop for now — no containers, no deployment. There is no `Dockerfile`; don't add one back without asking.

- **Backend:** `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` (from inside `backend/`, so `app.main` resolves). `GET /health` should return `{"status": "ok"}` once dependencies are installed — that's the one real endpoint, verify it first.
- **iOS:** open `Lens/Lens.xcodeproj` in Xcode and run on a physical device — ARKit and the camera don't work in the simulator. Point `Networking/APIClient.swift`'s base URL at your laptop's local network IP (not `localhost`), since a physical device can't reach the laptop's loopback address. The project uses Xcode 16's file-system-synchronized groups, so any file you add under `Lens/Lens/` shows up automatically — no `.pbxproj` editing needed.
- **Tests:** `cd backend && pytest` runs `tests/test_health.py`, the one real test.

## Working conventions

- Stub files have `// TODO: implement` (Swift) or `# TODO: implement` (Python) bodies with docstrings explaining intent. Fill those in; don't redesign the file layout without telling the other lanes — the layout is what lets four people edit in parallel.
- This is a hackathon: prioritize a working, demoable path over polish, generality, or error handling for cases that won't come up in the demo.
- Don't touch another lane's files unless you've coordinated — the API contract and the swap-point functions are the only things every lane needs to agree on.
