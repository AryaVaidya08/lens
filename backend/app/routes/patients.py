"""Read-only patient charts. Writes happen only through clinic sync."""

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.clinic.sync import sync_clinic_records
from app.db.accounts import patients_for_hcp, public_patient, reject_path_id
from app.db.database import get_db
from app.db.sessions import current_hcp

router = APIRouter(tags=["patients"])


@router.post("/patients/sync")
def sync_patients(hcp: dict = Depends(current_hcp), db: Database = Depends(get_db)) -> dict:
    """Refresh this doctor's charts from the clinic source. Never synces every HCP."""
    try:
        result = sync_clinic_records(db, hcp_id=hcp["_id"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Clinic source is unavailable.") from exc
    fresh = db.hcps.find_one({"_id": hcp["_id"]})
    result["patients"] = patients_for_hcp(db, fresh)
    return result


@router.get("/patients/{patient_id}")
def get_patient(
    patient_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    if patient_id == "sync":
        raise HTTPException(status_code=404, detail="Unknown patient_id: sync")
    patient_id = reject_path_id(patient_id, "patient_id")
    row = db.patients.find_one({"_id": patient_id})
    if row is None or row.get("hcp_id") != hcp["_id"]:
        raise HTTPException(status_code=404, detail="Unknown patient_id: %s" % patient_id)
    return public_patient(row)
