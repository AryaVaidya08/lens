"""
Pytest configuration.

Uses an in-memory MongoDB mock so tests never require a running mongod
and never write into the demo `lens` database.
"""

import os

os.environ["MONGODB_URI"] = "mongomock://localhost"
os.environ["MONGODB_DB"] = "lens_test"
os.environ.setdefault("SEED_ON_STARTUP", "1")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    Shared TestClient for all route tests.

    Entering TestClient as a context manager is important because it runs
    the FastAPI lifespan, including database setup and retrieval ingestion.
    """
    with TestClient(app) as test_client:
        yield test_client