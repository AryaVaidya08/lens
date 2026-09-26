"""
Drug summary + follow-up Q&A endpoints.

Owned by: Voice & LLM lane (ask_question, retrieval weighting) and
Backend & data lane (get_summary, personalization plumbing).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/drug", tags=["drug"])


@router.get("/{drug_id}/summary")
def get_summary(drug_id: str, hcp_id: str) -> dict:
    """
    Personalized HUD content for a drug, tailored to the HCP's
    familiarity tier.

    Contract (see Models/DrugSummary.swift):
      -> { "drug_id": str, "name": str, "tier": "new" | "returning" | "expert",
           "headline": str, "bullets": list[str] }

    TODO: implement — call personalization/scorer.py::score_familiarity,
    then pick which fields of the drug dossier to surface based on tier
    ("new" -> basics, "expert" -> dosing/trial data).
    """
    # TODO: implement
    raise NotImplementedError


@router.post("/{drug_id}/ask")
def ask_question(drug_id: str, payload: dict) -> dict:
    """
    Voice follow-up question -> grounded, spoken-ready answer.

    Contract:
      <- { "hcp_id": str, "query": str }
      -> { "answer_text": str }

    TODO: implement — call retrieval/index.py::retrieve(drug_id, query)
    to get context chunks, then llm/client.py::generate_answer(query,
    context) to produce the answer. Do not call embeddings or the LLM
    API directly from this file.
    """
    # TODO: implement
    raise NotImplementedError
