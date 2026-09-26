"""
Demo data seeding.

Populates 3-4 mock HCPs and a handful of mock drugs before the demo, so
personalization has real starting state to show a delta against. Run
once at backend startup (see app/main.py's lifespan).

Owned by: Content & demo lane.
"""

from datetime import datetime, timedelta, timezone

from app.db.database import SessionLocal
from app.db.models import Drug, Engagement, HCP

DEMO_HCPS = [
    ("hcp_amara", "Dr. Amara Okafor", "Internal Medicine"),
    ("hcp_ben", "Dr. Ben Whitfield", "Cardiology"),
    ("hcp_priya", "Dr. Priya Nair", "Pediatrics"),
]

# drug_id must match a filename stem under backend/data/drug_docs/
DEMO_DRUGS = [
    ("ibuprofen", "Ibuprofen", "3-00000-00171", "Ibuprofen"),
    ("advil", "Advil", "3-05000-16803", "Ibuprofen"),
    ("tylenol", "Tylenol", "3-00045-15467", "Acetaminophen"),
    ("acetaminophen", "Acetaminophen", "3-00000-00172", "Acetaminophen"),
]

# Pre-existing engagement so the demo can show "expert" without three live
# scans: hcp_amara has already seen ibuprofen 3 times.
DEMO_ENGAGEMENTS = [
    ("hcp_amara", "ibuprofen", 3, timedelta(days=2)),
]


def seed() -> None:
    """Inserts demo HCPs, Drugs, and a couple of Engagement rows. Safe to call more than once."""
    db = SessionLocal()
    try:
        for hcp_id, name, specialty in DEMO_HCPS:
            if db.query(HCP).filter(HCP.id == hcp_id).first() is None:
                db.add(HCP(id=hcp_id, name=name, specialty=specialty))

        for drug_id, name, barcode, generic in DEMO_DRUGS:
            if db.query(Drug).filter(Drug.id == drug_id).first() is None:
                db.add(Drug(id=drug_id, name=name, barcode=barcode, generic_name=generic))

        db.commit()

        for hcp_id, drug_id, touch_count, age in DEMO_ENGAGEMENTS:
            existing = (
                db.query(Engagement)
                .filter(Engagement.hcp_id == hcp_id, Engagement.drug_id == drug_id)
                .first()
            )
            if existing is None:
                db.add(
                    Engagement(
                        hcp_id=hcp_id,
                        drug_id=drug_id,
                        touch_count=touch_count,
                        last_seen=datetime.now(timezone.utc) - age,
                    )
                )
        db.commit()
    finally:
        db.close()
