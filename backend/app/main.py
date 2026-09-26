"""
FastAPI application entrypoint.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.retrieval.ingest import ingest_docs
from app.routes import detect, drug, engagement, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build the in-memory RAG index when the backend starts.
    """

    try:
        entries = ingest_docs(settings.drug_docs_path)
        print(f"Loaded {len(entries)} drug-document chunks.")
    except FileNotFoundError as exc:
        # Allow the backend to start before the content team
        # adds the drug documents.
        print(f"Drug document ingestion skipped: {exc}")

    yield


app = FastAPI(
    title="HCP Spatial Copilot",
    lifespan=lifespan,
)

app.include_router(profile.router)
app.include_router(detect.router)
app.include_router(drug.router)
app.include_router(engagement.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}