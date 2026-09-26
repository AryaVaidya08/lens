"""
Demo data seeding.

Populates mock HCPs and drugs before the demo. Patient charts come
from clinic/EHR ingest (`app/clinic/sync.py`), not from this file.

Seeding is idempotent and safe to run on every backend startup.
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

# Physical demo bottles + iOS contract barcodes. Dossier files often
# only have NDCs, which do not match the UPC/EAN printed on the bottle.
DEMO_BARCODES = {
    "adderall": ["0363323012345", "0357844110014"],
    "lorazepam": ["0362135861018"],
    "biofreeze": ["0731124100009"],
}

# Give one persona prior familiarity so the personalization demo has
# a visible "returning/expert" state immediately.
PRESEEDED_ENGAGEMENTS = [
    ("hcp_002", "lorazepam", 2),
    ("hcp_001", "ibuprofen", 3),
]


DEMO_IDS = {row["_id"] for row in DEMO_HCPS}


def seed(db: Optional[Database] = None) -> None:
    """
    Idempotent: safe on every startup. Never deletes clinician documents,
    never resets touch counts, and never overwrites a password, profile,
    or chart a clinician already edited. Registered accounts use hcp_<hex> ids
    and live in `hcps` — seed only upserts the three demo ids.
    Never resets engagement counts accumulated during a demo run.
    """
    db = db if db is not None else get_database()

    # ------------------------------------------------------------------
    # HCP accounts
    # ------------------------------------------------------------------
    for demo in DEMO_HCPS:
        if demo["_id"] not in DEMO_IDS:
            continue
        existing = db.hcps.find_one({"_id": demo["_id"]})

        if existing is None:
            row = dict(demo)
            row["password_hash"] = hash_password(DEMO_PASSWORD)
            row["patient_ids"] = []
            row["created_at"] = datetime.now(timezone.utc)
            row["account_source"] = "seed"
            db.hcps.insert_one(row)
            continue

        # Existing clinicians keep whatever they saved in Edit profile.
        # Seed only fills secrets/lists that would leave the account unusable.
        patch = {}
        if not existing.get("password_hash"):
            patch["password_hash"] = hash_password(DEMO_PASSWORD)

        if "patient_ids" not in existing or existing.get("patient_ids") is None:
            patch["patient_ids"] = []

        if patch:
            db.hcps.update_one(
                {"_id": demo["_id"]},
                {"$set": patch},
            )

    # ------------------------------------------------------------------
    # Drug corpus
    # ------------------------------------------------------------------
    # The corpus is the source of truth for drug metadata. This includes
    # the larger llm-rag dossier corpus rather than a small hard-coded
    # list of drugs.
    dossiers = load_dossiers(settings.drug_docs_path)
    already = db.drugs.count_documents({})
    if already < len(dossiers):
        for dossier in dossiers.values():
            codes = list(DEMO_BARCODES.get(dossier.drug_id, []))
            if dossier.barcode:
                codes.append(dossier.barcode)
            codes = list(dict.fromkeys(code for code in codes if code))
            db.drugs.update_one(
                {"_id": dossier.drug_id},
                {
                    "$set": {
                        "name": dossier.name,
                        "barcode": codes[0] if codes else "",
                        "barcodes": codes,
                    }
                },
                upsert=True,
            )
    else:
        for drug_id, extra in DEMO_BARCODES.items():
            dossier = dossiers.get(drug_id)
            codes = list(extra)
            if dossier and dossier.barcode:
                codes.append(dossier.barcode)
            codes = list(dict.fromkeys(code for code in codes if code))
            if not codes:
                continue
            db.drugs.update_one(
                {"_id": drug_id},
                {
                    "$set": {
                        "barcode": codes[0],
                        "barcodes": codes,
                    }
                },
            )

    # ------------------------------------------------------------------
    # Demo engagement history
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc)

    for hcp_id, drug_id, touch_count in PRESEEDED_ENGAGEMENTS:
        if db.drugs.find_one({"_id": drug_id}) is None:
            continue

        db.engagements.update_one(
            {"_id": f"{hcp_id}:{drug_id}"},
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

    # ------------------------------------------------------------------
    # Clinic/EHR demo patients
    # ------------------------------------------------------------------
    sync_clinic_records(db)