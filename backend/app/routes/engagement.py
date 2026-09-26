"""
Engagement logging endpoint.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.database import Database

from app.db.database import get_db
from app.db.sessions import assert_same_hcp, current_hcp

router = APIRouter(prefix="/engagement", tags=["engagement"])


class EngagementRequest(BaseModel):
    hcp_id: str
    drug_id: str


@router.post("/log")
def log_engagement(
    payload: EngagementRequest,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, payload.hcp_id)
    if db.drugs.find_one({"_id": payload.drug_id}) is None:
        raise HTTPException(status_code=404, detail="Unknown drug_id: %s" % payload.drug_id)

    now = datetime.now(timezone.utc)
    key = "%s:%s" % (payload.hcp_id, payload.drug_id)
    db.engagements.update_one(
        {"_id": key},
        {
            "$inc": {"touch_count": 1},
            "$set": {"last_seen": now, "hcp_id": payload.hcp_id, "drug_id": payload.drug_id},
            "$setOnInsert": {"_id": key},
        },
        upsert=True,
    )
    row = db.engagements.find_one({"_id": key})
    return {"touch_count": row["touch_count"]}
