"""
Drug summary + follow-up Q&A endpoints.

Owned by: Voice & LLM lane (ask_question, retrieval weighting) and
Backend & data lane (get_summary, personalization plumbing).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import Drug
from ..llm.client import generate_answer
from ..personalization.scorer import build_summary_content, score_familiarity
from ..retrieval.index import retrieve

router = APIRouter(prefix="/drug", tags=["drug"])


@router.get("/{drug_id}/summary")
def get_summary(drug_id: str, hcp_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Personalized HUD content for a drug, tailored to the HCP's
    familiarity tier.

    Contract (see Models/DrugSummary.swift):
      -> { "drug_id": str, "name": str, "tier": "new" | "returning" | "expert",
           "headline": str, "bullets": list[str] }
    """
    drug = db.query(Drug).filter(Drug.id == drug_id).first()
    if drug is None:
        raise HTTPException(status_code=404, detail=f"Unknown drug_id: {drug_id}")

    tier = score_familiarity(hcp_id, drug_id)
    headline, bullets = build_summary_content(drug_id, tier)

    return {
        "drug_id": drug.id,
        "name": drug.name,
        "tier": tier,
        "headline": headline,
        "bullets": bullets,
    }


@router.post("/{drug_id}/ask")
def ask_question(drug_id: str, payload: dict) -> dict:
    """
    Voice follow-up question -> grounded, spoken-ready answer.

    Contract:
      <- { "hcp_id": str, "query": str }
      -> { "answer_text": str }
    """
    
    query = payload.get("query")

    if not isinstance(query, str) or not query.strip():
        raise HTTPException(
            status_code=400,
            detail="query must be a non-empty string",
        )

    try:
        context = retrieve(drug_id, query)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval failed: {exc}",
        )

    if not context:
        raise HTTPException(
            status_code=404,
            detail="No relevant information found for this drug.",
        )

    try:
        answer = generate_answer(query, context)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    return {"answer_text": answer}
