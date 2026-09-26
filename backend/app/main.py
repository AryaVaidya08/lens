"""
FastAPI application entrypoint.

Wires together all route modules behind one app instance. This is the
file `uvicorn app.main:app` points at.

Route ownership (see docs/team-context/ for the full breakdown):
  - profile.py     -> HCP profile + familiarity tier lookups
  - detect.py      -> barcode/OCR result -> drug identity
  - drug.py        -> personalized summary + RAG/LLM follow-up Q&A
  - engagement.py  -> engagement touch-count logging

`GET /health` is intentionally real (not a stub) so deployment can be
verified independently of everything else being finished.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from app.config import settings
from app.routes import detect, drug, engagement, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("SKIP_INGEST") != "1":
        from app.retrieval.ingest import ingest_docs

        ingest_docs(settings.drug_docs_path)
    yield


app = FastAPI(title="HCP Spatial Copilot", lifespan=lifespan)

app.include_router(profile.router)
app.include_router(detect.router)
app.include_router(drug.router)
app.include_router(engagement.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
