"""
HCP profile endpoint.

Owned by: Backend & data lane.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{hcp_id}")
def get_profile(hcp_id: str) -> dict:
    """
    Returns HCP specialty and familiarity tier per drug.

    Contract (see ios/APIClient.getProfile and Models/HCP.swift):
      -> { "hcp_id": str, "name": str, "specialty": str,
           "familiarity": { drug_id: "new" | "returning" | "expert" } }

    TODO: implement — look up the HCP row via db/database.py, then call
    personalization/scorer.py::score_familiarity for each drug the HCP
    has an Engagement row for.
    """
    # TODO: implement
    raise NotImplementedError
