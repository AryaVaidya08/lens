import os
import shutil
import tempfile

# Must run before app.config (and therefore app.db.database, which builds
# the engine at import time) is imported anywhere — including by other test
# modules pytest collects after this file. Without this, tests write to the
# same ./hcp.db the dev server uses, corrupting demo personas and making
# reruns fail (e.g. hcp_priya ends up "expert" after one run of the suite).
_TEST_DB_DIR = tempfile.mkdtemp(prefix="lens-test-db-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    yield
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


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
