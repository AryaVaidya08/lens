"""
FastAPI application entrypoint.

Wires together all route modules behind one app instance. This is the
file `uvicorn app.main:app` points at.
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

        try:
            chunks = ingest_docs(settings.drug_docs_path)
            print(f"Loaded {len(chunks)} drug-document chunks.")
        except FileNotFoundError as exc:
            print(f"Drug document ingestion skipped: {exc}")

    from app.db.database import init_db

    init_db()
    from app.db.seed import seed

    seed()

    yield


app = FastAPI(title="HCP Spatial Copilot", lifespan=lifespan)

app.include_router(profile.router)
app.include_router(detect.router)
app.include_router(drug.router)
app.include_router(engagement.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
