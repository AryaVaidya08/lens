"""
Engagement logging endpoint.

Owned by: Backend & data lane. This is the write side of the
personalization loop described in docs/architecture.md — every scan
increments a touch count that personalization/scorer.py reads back.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/engagement", tags=["engagement"])


@router.post("/log")
def log_engagement(payload: dict) -> dict:
    """
    Increments touch count for an (hcp_id, drug_id) pair and updates
    last_seen. Called once per successful detect -> summary cycle.

    Contract:
      <- { "hcp_id": str, "drug_id": str }
      -> { "touch_count": int }

    TODO: implement — upsert the Engagement row (db/models.py) for this
    hcp_id/drug_id pair.
    """
    # TODO: implement
    raise NotImplementedError
