"""
FastAPI application entrypoint.

Wires together all route modules behind one app instance. This is the
file `uvicorn app.main:app` points at.

Route ownership:
  - auth.py        -> HCP register + email login
  - profile.py     -> HCP profile, chats, patient folder list
  - patients.py    -> read-only charts + clinic/EHR sync
  - detect.py      -> barcode/OCR result -> drug identity
  - drug.py        -> personalized summary + RAG/LLM follow-up Q&A
  - engagement.py  -> engagement touch-count logging

`GET /health` is intentionally real so deployment can be verified
independently of everything else being finished.
"""

from __future__ import annotations

import logging

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.database import close_client, ensure_indexes, get_database
from app.db.mongo import store_info
from app.db.seed import seed
from app.detection import catalog as detect_catalog
from app.retrieval import index
from app.retrieval.embed import using_model
from app.retrieval.ingest import ingest_docs
from app.routes import auth, detect, drug, engagement, patients, profile, medication_reviews

logger = logging.getLogger("uvicorn.error")

from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize MongoDB and the drug retrieval index at startup, then
    close the MongoDB client during shutdown.
    """
    db = get_database()
    info = store_info()
    logger.info(
        "Clinician accounts persist in MongoDB %s (collection %s, %s)",
        info["mongodb_db"],
        info["accounts_collection"],
        info["mongodb_kind"],
    )
    if settings.seed_on_startup:
        seed(db)

    ensure_indexes(db)
    detect_count = detect_catalog.load(db)
    logger.info("Detect catalog loaded %s drugs.", detect_count)

    # Preserve the llm-rag SKIP_INGEST switch so large corpus ingestion
    # can be skipped during development when the index is already loaded.
    if os.environ.get("SKIP_INGEST") != "1":
        try:
            chunks = ingest_docs(settings.drug_docs_path)
            index.load(chunks)
            print(f"Loaded {len(chunks)} drug-document chunks.")
        except FileNotFoundError as exc:
            print(f"Drug document ingestion skipped: {exc}")
        except Exception as exc:
            print(f"Drug document ingestion failed; API still starting: {exc}")
    else:
        print("Drug document ingestion skipped (SKIP_INGEST=1).")

    yield

    close_client()


# Disable automatic slash redirects because redirects can turn a POST
# request into a GET and discard the request body.
app = FastAPI(
    title="HCP Spatial Copilot",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(patients.router)
app.include_router(medication_reviews.router)
app.include_router(detect.router)
app.include_router(drug.router)
app.include_router(engagement.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict:
    """
    Reports how the retrieval, LLM, and database layers are running.
    """
    body = {
        "indexed_chunks": index.chunk_count(),
        "detect_catalog": detect_catalog.size(),
        "embeddings": "sentence-transformers" if using_model() else "lexical-fallback",
        "llm": "api" if settings.llm_enabled else "offline-fallback",
    }
    body.update(store_info())
    return body
