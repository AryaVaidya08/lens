"""
Engagement logging endpoint.

Owned by: Backend & data lane. This is the write side of the
personalization loop described in docs/architecture.md — every scan
increments a touch count that personalization/scorer.py reads back.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Drug, Engagement, HCP

router = APIRouter(prefix="/engagement", tags=["engagement"])


@router.post("/log")
def log_engagement(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Increments touch count for an (hcp_id, drug_id) pair and updates
    last_seen. Called once per successful detect -> summary cycle.

    Contract:
      <- { "hcp_id": str, "drug_id": str }
      -> { "touch_count": int }
    """
    hcp_id = payload.get("hcp_id")
    drug_id = payload.get("drug_id")
    if not hcp_id or not drug_id:
        raise HTTPException(status_code=400, detail="hcp_id and drug_id are required")

    if db.query(HCP).filter(HCP.id == hcp_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown hcp_id: {hcp_id}")
    if db.query(Drug).filter(Drug.id == drug_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Unknown drug_id: {drug_id}")

    row = (
        db.query(Engagement)
        .filter(Engagement.hcp_id == hcp_id, Engagement.drug_id == drug_id)
        .first()
    )
    if row is None:
        row = Engagement(hcp_id=hcp_id, drug_id=drug_id, touch_count=0)
        db.add(row)

    row.touch_count += 1
    row.last_seen = datetime.now(timezone.utc)
    db.commit()

    return {"touch_count": row.touch_count}
