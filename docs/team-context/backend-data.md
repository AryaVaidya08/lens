# Lane context: Backend & data

Read `CLAUDE.md` at the repo root first — this doc only covers what's specific to your lane.

## What you own

The FastAPI service, the SQLite schema, and the plumbing that makes the retrieval index buildable (not the retrieval logic itself — see Voice & LLM lane).

- `backend/app/main.py` — app instance, router wiring, `/health` (already real)
- `backend/app/config.py` — env-based settings
- `backend/app/routes/profile.py` — `GET /profile/{hcp_id}`
- `backend/app/routes/detect.py` — `POST /detect`
- `backend/app/routes/drug.py` — `GET /drug/{drug_id}/summary` (the `ask` route in the same file belongs to Voice & LLM)
- `backend/app/routes/engagement.py` — `POST /engagement/log`
- `backend/app/db/models.py`, `database.py` — SQLAlchemy models + session
- `backend/app/retrieval/ingest.py` — the mechanics of reading `data/drug_docs/` and chunking (Voice & LLM owns `embed.py`/`index.py`, the retrieval math)

## What you depend on (don't break, coordinate before changing)

- `backend/app/personalization/scorer.py::score_familiarity` (Content & demo lane) — `routes/profile.py` and `routes/drug.py` both call this. If its return values change (currently `"new" | "returning" | "expert"`), every caller needs updating.
- `Lens/Lens/Models/HCP.swift`, `Drug.swift`, `DrugSummary.swift` (AR & detection / Networking lane) — your route responses must match these shapes exactly, field names included.

## Suggested build order

1. `db/models.py` + `db/database.py` — get SQLite creating tables on startup.
2. `db/seed.py` — coordinate with Content & demo lane on what mock HCPs/drugs look like, but you own making `seed()` actually run.
3. `routes/detect.py` and `routes/engagement.py` — the simplest routes, get them returning real data against the seeded DB.
4. `routes/profile.py` and the `summary` half of `routes/drug.py` — once `personalization/scorer.py` has a real implementation to call.
5. Confirm `retrieval/ingest.py` runs at startup without erroring, even before retrieval itself is fully implemented (an empty/stub index is fine short-term) — this unblocks Voice & LLM's `retrieve()` work.

## Pitfalls specific to this lane

- **SQLite + FastAPI async:** `check_same_thread=False` is already set in `database.py` — don't remove it, or you'll get thread errors under FastAPI's default threadpool for sync route handlers.
- **Keep `routes/*.py` thin.** Business logic (familiarity scoring, retrieval, LLM calls) belongs in `personalization/`, `retrieval/`, `llm/` — routes should just call into those and shape the HTTP response. This is what keeps the swap points in `CLAUDE.md` honest.
- Run `uvicorn app.main:app --reload` from inside `backend/` (not the repo root) — the import path `app.main` assumes `backend/` is the working directory.
- Test with `curl http://localhost:8000/health` before anything else — it's the one endpoint guaranteed to work once dependencies are installed.

## Definition of done for the hackathon

Every route returns real data backed by the seeded SQLite DB, `/detect` and `/engagement/log` correctly update state that `/profile` and `/drug/.../summary` reflect on the next call — i.e., the loop closes end-to-end at the API layer, independent of whether the iOS app is hitting it yet.
