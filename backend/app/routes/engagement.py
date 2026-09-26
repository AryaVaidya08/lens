"""
Engagement logging endpoint.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pymongo.database import Database

from app.db.accounts import owned_patient, reject_path_id
from app.db.database import get_db
from app.db.sessions import assert_same_hcp, current_hcp

router = APIRouter(prefix="/engagement", tags=["engagement"])


class EngagementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hcp_id: str = Field(max_length=64)
    drug_id: str = Field(max_length=64)
    patient_id: Optional[str] = Field(default=None, max_length=64)


@router.post("/log")
def log_engagement(
    payload: EngagementRequest,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    """
    Increments touch count for an (hcp_id, drug_id) pair and updates
    last_seen.

    Called once per successful detect -> summary cycle.

    Contract:
      <- { "hcp_id": str, "drug_id": str }
      -> { "touch_count": int }
    """
    assert_same_hcp(hcp, payload.hcp_id)
    drug_id = reject_path_id(payload.drug_id, "drug_id")
    if db.drugs.find_one({"_id": drug_id}) is None:
        raise HTTPException(status_code=404, detail="Unknown drug_id: %s" % payload.drug_id)

    now = datetime.now(timezone.utc)
    owner = hcp["_id"]
    key = "%s:%s" % (owner, drug_id)
    fields = {"last_seen": now, "hcp_id": owner, "drug_id": drug_id}
    requested = (payload.patient_id or "").strip()
    if requested:
        patient = owned_patient(db, hcp, requested)
        fields["last_patient_id"] = patient["_id"]
    db.engagements.update_one(
        {"_id": key},
        {
            "$inc": {"touch_count": 1},
            "$set": fields,
            "$setOnInsert": {"_id": key},
        },
        upsert=True,
    )

    row = db.engagements.find_one({"_id": key})

    return {"touch_count": row["touch_count"]}