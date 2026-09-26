"""
Write parsed clinic records into Mongo. This is the only writer for patients.
"""

from typing import Dict, List, Optional

from pymongo.database import Database

from app.clinic.ingest import load_clinic_records, records_for_hcp
from app.db.mongo import get_database


def sync_clinic_records(db: Optional[Database] = None, hcp_id: Optional[str] = None) -> Dict[str, int]:
    """
    Upsert charts from the clinic source. Each HCP's patient_ids becomes
    the ordered list of ids that source assigned to that doctor.
    """
    db = db if db is not None else get_database()
    records = load_clinic_records()
    if hcp_id:
        records = records_for_hcp(records, hcp_id)
    by_hcp = {}  # type: Dict[str, List[str]]
    for row in records:
        owner = row["hcp_id"]
        db.patients.update_one({"_id": row["_id"]}, {"$set": row}, upsert=True)
        by_hcp.setdefault(owner, []).append(row["_id"])
    for owner, ids in by_hcp.items():
        if db.hcps.find_one({"_id": owner}) is None:
            continue
        db.hcps.update_one({"_id": owner}, {"$set": {"patient_ids": ids}})
    return {"imported": len(records), "clinicians": len(by_hcp)}
