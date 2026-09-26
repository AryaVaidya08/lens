"""
FastAPI application entrypoint.

Wires together all route modules behind one app instance. This is the
file `uvicorn app.main:app` points at.

Route ownership (see docs/team-context/ for the full breakdown):
  - auth.py        -> HCP register + email login
  - profile.py     -> HCP profile, chats, patient folder list
  - patients.py    -> read-only charts + clinic/EHR sync
  - detect.py      -> barcode/OCR result -> drug identity
  - drug.py        -> personalized summary + RAG/LLM follow-up Q&A
  - engagement.py  -> engagement touch-count logging

`GET /health` is intentionally real (not a stub) so deployment can be
verified independently of everything else being finished.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.database import close_client, ensure_indexes, get_database
from app.db.seed import seed
from app.retrieval import index
from app.retrieval.embed import using_model
from app.retrieval.ingest import ingest_docs
from app.routes import auth, detect, drug, engagement, patients, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_database()
    if settings.seed_on_startup:
        seed(db)
    ensure_indexes(db)
    index.load(ingest_docs(settings.drug_docs_path))
    yield
    close_client()


# Slash redirects turn POST /detect/ into GET /detect and drop the body.
# The iOS client doesn't add a trailing slash; this keeps a stray one from
# looking like a dead backend.
app = FastAPI(title="HCP Spatial Copilot", lifespan=lifespan, redirect_slashes=False)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(patients.router)
app.include_router(detect.router)
app.include_router(drug.router)
app.include_router(engagement.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict:
    """
    Reports how the two swap points are actually running, so a demo machine
    that silently fell back to offline retrieval or offline answers is visible
    from one curl instead of from the logs.
    """
    return {
        "indexed_chunks": index.chunk_count(),
        "embeddings": "sentence-transformers" if using_model() else "lexical-fallback",
        "llm": "api" if settings.llm_enabled else "offline-fallback",
        "database": "mongodb",
        "mongodb_db": settings.mongodb_db,
    }
