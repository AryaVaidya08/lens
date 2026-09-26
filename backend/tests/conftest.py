"""
Pytest configuration.

Uses an in-memory MongoDB mock so tests never require a running mongod
and never write into the demo `lens` database.
"""

import os
import shutil
import tempfile
from pathlib import Path

os.environ["MONGODB_URI"] = "mongomock://localhost"
os.environ["MONGODB_DB"] = "lens_test"
os.environ.setdefault("SEED_ON_STARTUP", "1")

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.mongo import get_database
from app.db.passwords import hash_password
from app.db.seed import DEMO_HCPS
from app.main import app
from app.retrieval import index
from app.retrieval.ingest import ingest_docs
from app.routes import auth as auth_routes

_DEMO_PROFILE_KEYS = (
    "name",
    "first_name",
    "last_name",
    "email",
    "professional_role",
    "credentials",
    "specialty",
    "organization",
    "practice_setting",
    "city",
    "region",
    "country",
)

_DEMO_DOCS = (
    "adderall.txt",
    "lorazepam.txt",
    "biofreeze.txt",
    "ibuprofen.txt",
    "tylenol.txt",
    "advil.txt",
)


def _load_demo_index() -> None:
    """Index the six demo dossiers so ask tests work with SKIP_INGEST=1."""
    if index.chunk_count() >= 15:
        return
    src = Path(settings.drug_docs_path)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        for name in _DEMO_DOCS:
            path = src / name
            if path.is_file():
                shutil.copy(path, dest / name)
        chunks = ingest_docs(str(dest))
        index.load(chunks)


_load_demo_index()


_DEMO_PASSWORD_HASH = hash_password("demo")


@pytest.fixture(autouse=True)
def _restore_demo_logins():
    """Reset demo passwords, profile fields, and the login rate limiter."""
    auth_routes._ATTEMPTS.clear()
    db = get_database()
    db.hcps.update_many(
        {"_id": {"$in": ["hcp_001", "hcp_002", "hcp_003"]}},
        {"$set": {"password_hash": _DEMO_PASSWORD_HASH}},
    )
    for row in DEMO_HCPS:
        db.hcps.update_one(
            {"_id": row["_id"]},
            {"$set": {key: row[key] for key in _DEMO_PROFILE_KEYS if key in row}},
        )
    yield
    auth_routes._ATTEMPTS.clear()


@pytest.fixture(scope="session")
def client():
    """
    Shared TestClient for all route tests.

    Entering TestClient as a context manager is important because it runs
    the FastAPI lifespan, including database setup and retrieval ingestion.
    """
    with TestClient(app) as test_client:
        _load_demo_index()
        yield test_client
