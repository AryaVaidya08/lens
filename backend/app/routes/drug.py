"""
Drug summary + follow-up Q&A endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.database import Database

from app.config import settings
from app.db.database import get_db
from app.db.sessions import assert_same_hcp, current_hcp
from app.llm.client import generate_answer
from app.personalization.scorer import score_familiarity
from app.retrieval.index import retrieve
from app.retrieval.ingest import load_dossiers

router = APIRouter(prefix="/drug", tags=["drug"])

SECTIONS_BY_TIER = {
    "new": ("Basics", "Warnings"),
    "returning": ("Dosing", "Side effects", "Warnings"),
    "expert": ("Trial data", "Interactions", "Dosing"),
}
MAX_BULLETS = 3


class AskRequest(BaseModel):
    hcp_id: str
    query: str


@router.get("/{drug_id}/summary")
def get_summary(
    drug_id: str,
    hcp_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)
    drug = db.drugs.find_one({"_id": drug_id})
    if drug is None:
        raise HTTPException(status_code=404, detail="Unknown drug_id: %s" % drug_id)

    tier = score_familiarity(hcp["_id"], drug_id, db)
    dossier = load_dossiers(settings.drug_docs_path).get(drug_id)
    if dossier is None:
        return {
            "drug_id": drug["_id"],
            "name": drug["name"],
            "tier": tier,
            "headline": drug["name"],
            "bullets": [],
        }

    bullets = []
    for section in SECTIONS_BY_TIER[tier]:
        for bullet in dossier.bullets(section):
            if bullet not in bullets:
                bullets.append(bullet)

    return {
        "drug_id": drug["_id"],
        "name": dossier.name,
        "tier": tier,
        "headline": dossier.headline or drug["name"],
        "bullets": bullets[:MAX_BULLETS],
    }


@router.post("/{drug_id}/ask")
def ask_question(
    drug_id: str,
    payload: AskRequest,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, payload.hcp_id)
    if db.drugs.find_one({"_id": drug_id}) is None:
        raise HTTPException(status_code=404, detail="Unknown drug_id: %s" % drug_id)
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    tier = score_familiarity(hcp["_id"], drug_id, db)
    context = retrieve(drug_id, payload.query)
    answer = generate_answer(payload.query, context, tier)
    db.chats.insert_one(
        {
            "hcp_id": hcp["_id"],
            "drug_id": drug_id,
            "question": payload.query.strip(),
            "answer": answer,
            "asked_at": datetime.now(timezone.utc),
        }
    )
    return {"answer_text": answer}
