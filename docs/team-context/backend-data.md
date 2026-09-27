# Lane context: Backend & data

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane. This doc has been refreshed against the current codebase (unlike some of the other lane docs, which may still describe the original scaffold — cross-check anything that looks stale).

## What you own

The FastAPI service, real accounts, the MongoDB schema, and the plumbing that makes the retrieval index buildable (not the retrieval logic itself — see Voice & LLM lane).

- `backend/app/main.py` — app instance, router wiring, lifespan startup (Mongo connect, seed, detect catalog, doc ingestion), `/health` + `/status`
- `backend/app/config.py` — env-based settings (`MONGODB_URI`, `XAI_API_KEY`, etc. — see this file for the full list)
- `backend/app/routes/auth.py` — register/login/logout/change-password/forgot-password/reset-password. Hashed passwords, bearer session tokens, per-key rate limiting, recovery-code-based reset.
- `backend/app/routes/profile.py` — HCP profile (`GET`/`PATCH /profile/{hcp_id}`), saved chat conversations (list/rename/delete), and patient charts (list/create/get).
- `backend/app/routes/medication_reviews.py` — save/update a medication-review draft per patient, with optimistic concurrency via a `revision` field. Comparison is deliberately literal (no inferred dose equivalence or treatment advice).
- `backend/app/routes/detect.py` — `POST /detect`, resolves barcode/OCR text against `app/detection/catalog.py`'s in-memory fuzzy-match catalog.
- `backend/app/routes/drug.py` — `GET /drug/search`, `GET /drug/{drug_id}/summary` (the `ask` route in the same file belongs to Voice & LLM).
- `backend/app/routes/engagement.py` — `POST /engagement/log`.
- `backend/app/db/` — `database.py` (Mongo connection + `get_db` dependency), `mongo.py` (client/store info), `accounts.py`, `passwords.py` (hashing, recovery codes), `sessions.py` (bearer tokens, `current_hcp` dependency), `resets.py` (reset tickets), `seed.py` (demo HCPs + drug catalog, idempotent on every startup).
- `backend/app/detection/catalog.py` — builds the in-memory barcode/OCR-to-drug lookup once after seed, so `/detect` doesn't hit Mongo or the dossier folder on every camera frame.
- `backend/app/retrieval/ingest.py` — the mechanics of reading `data/drug_docs/` and chunking (Voice & LLM owns `embed.py`/`index.py`, the retrieval math).

## What you depend on (don't break, coordinate before changing)

- `backend/app/personalization/scorer.py::score_familiarity` and `resolve_specialty` (Content & demo lane) — `routes/profile.py` and `routes/drug.py` both call these. Tier values are `"new" | "returning" | "expert"`; specialty resolution maps a free-text specialty onto one of ~19 dossier-section groupings. If either return shape changes, every caller needs updating.
- `Lens/Lens/Models/HCP.swift`, `Drug.swift`, `DrugSummary.swift`, `Patient.swift`, `MedicationReview.swift` (iOS side) and `frontend/src/api.js` (web side) — your route responses must match these shapes exactly, field names included.

## Current state

All routes above are implemented against real MongoDB (Atlas or local; `mongomock` in-memory for tests — see `backend/app/config.py::mongodb_kind`), not stubs. `backend/tests/` (~25 files) covers auth, patients, scoring, ingestion, retrieval, and end-to-end flows — run `pytest` before assuming a route is broken; check the test first. Remaining backend work tends to be in edge-case handling (concurrent medication-review edits, session/token expiry UX) rather than first builds.

## Pitfalls specific to this lane

- **Mongo, not SQLite/SQLAlchemy.** There's no ORM layer — routes get a `pymongo.database.Database` via `app/db/database.py::get_db` and query collections directly. Don't reintroduce SQLAlchemy models.
- **Session auth is real**, via `app/db/sessions.py::current_hcp` as a FastAPI dependency — routes are scoped to the authenticated session, not a client-supplied `hcp_id` string. Don't add a route that trusts a path/query `hcp_id` without going through this dependency.
- **Keep `routes/*.py` thin.** Business logic (familiarity/specialty scoring, retrieval, LLM calls, patient-chart checks) belongs in `personalization/`, `retrieval/`, `llm/` — routes should just call into those and shape the HTTP response. This is what keeps the swap points in `CLAUDE.md` honest.
- Run `uvicorn app.main:app --reload` from inside `backend/` (not the repo root) — the import path `app.main` assumes `backend/` is the working directory.
- Test with `curl http://localhost:8000/health` and `/status` before anything else — `/status` tells you which Mongo it's actually talking to, whether embeddings are real or lexical-fallback, and whether the LLM key is configured.

## Definition of done for the hackathon

Every route returns real data backed by MongoDB, `/detect` and `/engagement/log` correctly update state that `/profile` and `/drug/.../summary` reflect on the next call, auth actually gates access to another HCP's data, and patient charts / medication reviews round-trip correctly from both the iOS app and the web dashboard against the same backend.
