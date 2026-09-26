import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    Shared TestClient for all route tests. Must be entered as a context
    manager — a bare TestClient(app) never runs FastAPI's lifespan, so
    ingest_docs() (which populates the retrieval index) never fires and
    /drug/{id}/ask silently sees an empty index.
    """
    with TestClient(app) as test_client:
        yield test_client
