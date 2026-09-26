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

# Mongo is the only source of truth for patients (no more clinic_records/
# JSON import). These mirror the old clinic-export fixtures so existing
# test assertions (names, allergies, ownership) keep working.
_DEMO_PATIENTS = (
    {
        "_id": "pat_001",
        "hcp_id": "hcp_001",
        "external_id": "MRN-10482",
        "source": "riverside-ehr",
        "first_name": "Elena",
        "last_name": "Vasquez",
        "birth_date": "1972-03-14",
        "age": None,
        "weight_kg": 72.5,
        "sex": "Female",
        "medical_history": "Type 2 diabetes, hypertension",
        "allergies": "Penicillin, amphetamines",
        "current_medications": "Metformin 1000 mg BID",
        "notes": "Considering stimulant coverage for ADHD symptoms.",
    },
    {
        "_id": "pat_002",
        "hcp_id": "hcp_001",
        "external_id": "MRN-11820",
        "source": "riverside-ehr",
        "first_name": "Marcus",
        "last_name": "Hale",
        "birth_date": "",
        "age": 31,
        "weight_kg": 88.0,
        "sex": "Male",
        "medical_history": "Anxiety, prior ankle sprain",
        "allergies": "Sentitive Skin",
        "current_medications": "None",
        "notes": "Asked about topical NSAIDs for training soreness.",
    },
    {
        "_id": "pat_003",
        "hcp_id": "hcp_002",
        "external_id": "MRN-22014",
        "source": "piedmont-heart-ehr",
        "first_name": "Priya",
        "last_name": "Shah",
        "birth_date": "",
        "age": 67,
        "weight_kg": 61.0,
        "sex": "Female",
        "medical_history": "Atrial fibrillation, osteoporosis",
        "allergies": "Sulfa",
        "current_medications": "Apixaban, metoprolol",
        "notes": "Watch benzodiazepine use with fall risk.",
    },
    {
        "_id": "pat_004",
        "hcp_id": "hcp_003",
        "external_id": "MRN-33109",
        "source": "emory-endocrine-ehr",
        "first_name": "Owen",
        "last_name": "Blake",
        "birth_date": "",
        "age": 42,
        "weight_kg": 96.0,
        "sex": "Male",
        "medical_history": "Type 1 diabetes, hypothyroidism",
        "allergies": "Latex",
        "current_medications": "Insulin aspart, levothyroxine",
        "notes": "Weight and A1C trending up this quarter.",
    },
)

_DEMO_PATIENT_IDS_BY_HCP = {
    "hcp_001": ["pat_001", "pat_002"],
    "hcp_002": ["pat_003"],
    "hcp_003": ["pat_004"],
}


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


@pytest.fixture(autouse=True)
def _restore_demo_patients():
    """Reset the four demo charts and their owning HCP's patient_ids.

    Patients live only in Mongo now, so tests that mutate charts or steal
    ownership need a clean baseline each run, same idea as
    _restore_demo_logins above.
    """
    db = get_database()
    for row in _DEMO_PATIENTS:
        db.patients.update_one({"_id": row["_id"]}, {"$set": row}, upsert=True)
    for hcp_id, patient_ids in _DEMO_PATIENT_IDS_BY_HCP.items():
        db.hcps.update_one({"_id": hcp_id}, {"$set": {"patient_ids": list(patient_ids)}})
    yield


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
