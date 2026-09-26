"""
Demo data seeding.

Populates mock HCPs and drugs before the demo. Patient charts come
from clinic/EHR ingest (`app/clinic/sync.py`), not from this file.
"""

from datetime import datetime, timezone
from typing import Optional

from pymongo.database import Database

from app.clinic.sync import sync_clinic_records
from app.config import settings
from app.db.mongo import get_database
from app.db.passwords import hash_password
from app.retrieval.ingest import load_dossiers

# These IDs must match HCP.demoProfiles in Lens/Lens/Models/HCP.swift.
# Email login for each demo account is the address below / password "demo".
DEMO_HCPS = [
    {
        "_id": "hcp_001",
        "name": "Dr. Maya Patel",
        "first_name": "Maya",
        "last_name": "Patel",
        "email": "maya.patel@lens.demo",
        "professional_role": "Physician",
        "credentials": "MD",
        "specialty": "Primary Care",
        "organization": "Riverside Family Clinic",
        "practice_setting": "Outpatient Clinic",
        "city": "Atlanta",
        "region": "GA",
        "country": "United States",
    },
    {
        "_id": "hcp_002",
        "name": "Dr. James Chen",
        "first_name": "James",
        "last_name": "Chen",
        "email": "james.chen@lens.demo",
        "professional_role": "Physician",
        "credentials": "MD",
        "specialty": "Cardiology",
        "organization": "Piedmont Heart",
        "practice_setting": "Hospital",
        "city": "Atlanta",
        "region": "GA",
        "country": "United States",
    },
    {
        "_id": "hcp_003",
        "name": "Dr. Sofia Ramirez",
        "first_name": "Sofia",
        "last_name": "Ramirez",
        "email": "sofia.ramirez@lens.demo",
        "professional_role": "Physician",
        "credentials": "MD",
        "specialty": "Endocrinology",
        "organization": "Emory Endocrine",
        "practice_setting": "Academic Medical Center",
        "city": "Atlanta",
        "region": "GA",
        "country": "United States",
    },
]

DEMO_PASSWORD = "demo"

PRESEEDED_ENGAGEMENTS = [("hcp_002", "lorazepam", 2)]


def seed(db: Optional[Database] = None) -> None:
    """
    Idempotent: safe on every startup. Never resets touch counts that
    were accumulated during a demo run, and never overwrites a password
    or chart a clinician already edited.
    """
    db = db if db is not None else get_database()

    for demo in DEMO_HCPS:
        existing = db.hcps.find_one({"_id": demo["_id"]})
        if existing is None:
            row = dict(demo)
            row["password_hash"] = hash_password(DEMO_PASSWORD)
            row["patient_ids"] = []
            db.hcps.insert_one(row)
            continue
        patch = {}
        for key, value in demo.items():
            if key == "_id":
                continue
            if not existing.get(key):
                patch[key] = value
        if not existing.get("password_hash"):
            patch["password_hash"] = hash_password(DEMO_PASSWORD)
        if "patient_ids" not in existing or existing.get("patient_ids") is None:
            patch["patient_ids"] = []
        if patch:
            db.hcps.update_one({"_id": demo["_id"]}, {"$set": patch})

    for dossier in load_dossiers(settings.drug_docs_path).values():
        db.drugs.update_one(
            {"_id": dossier.drug_id},
            {"$set": {"name": dossier.name, "barcode": dossier.barcode}},
            upsert=True,
        )

    now = datetime.now(timezone.utc)
    for hcp_id, drug_id, touch_count in PRESEEDED_ENGAGEMENTS:
        if db.drugs.find_one({"_id": drug_id}) is None:
            continue
        db.engagements.update_one(
            {"_id": "%s:%s" % (hcp_id, drug_id)},
            {
                "$setOnInsert": {
                    "hcp_id": hcp_id,
                    "drug_id": drug_id,
                    "touch_count": touch_count,
                    "last_seen": now,
                }
            },
            upsert=True,
        )

    sync_clinic_records(db)
