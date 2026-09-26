"""
HCP profile endpoint.

Owned by: Backend & data lane.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Engagement, HCP
from app.personalization.scorer import score_familiarity

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{hcp_id}")
def get_profile(hcp_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Returns HCP specialty and familiarity tier per drug.

    Contract (see Models/HCP.swift):
      -> { "hcp_id": str, "name": str, "specialty": str,
           "familiarity": { drug_id: "new" | "returning" | "expert" } }
    """
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if hcp is None:
        raise HTTPException(status_code=404, detail=f"Unknown hcp_id: {hcp_id}")

    drug_ids = [
        row.drug_id
        for row in db.query(Engagement).filter(Engagement.hcp_id == hcp_id).all()
    ]
    familiarity = {drug_id: score_familiarity(hcp_id, drug_id) for drug_id in drug_ids}

    return {
        "hcp_id": hcp.id,
        "name": hcp.name,
        "specialty": hcp.specialty,
        "familiarity": familiarity,
    }
