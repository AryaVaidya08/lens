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

`Lens/` (the Xcode project) and `backend/` are independent; the API contract above is the only thing that couples them. Build against the contract, not against each other's code.

## Team lanes

- **AR & detection** — camera, ARKit, on-device barcode/OCR
- **Backend & data** — FastAPI, SQLite schema, retrieval ingestion
- **Voice & LLM** — speech I/O, RAG retrieval weighting, LLM integration
- **Content & demo** — mock drug dossiers, personalization tuning, demo script

Each lane has a dedicated context doc in `docs/team-context/` — read yours before you start, and hand it to your coding agent as context. `CLAUDE.md` at the repo root covers the project-wide rules every lane shares.

## Setup

Everything runs locally on a laptop — no containers, no deployment, for now.

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Verify it's up: `curl http://localhost:8000/health` should return `{"status": "ok"}`.

**iOS:** open `Lens/Lens.xcodeproj` in Xcode and run on a physical device (ARKit and the camera don't work in the simulator). Point `Lens/Lens/Networking/APIClient.swift`'s base URL at your laptop's local IP (not `localhost`) so a physical device can reach the backend over the same Wi-Fi network.
