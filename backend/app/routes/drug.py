"""
Drug summary + follow-up Q&A endpoints.
"""

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.db.accounts import owned_patient, reject_path_id
from app.db.database import get_db
from app.db.sessions import assert_same_hcp, current_hcp
from app.llm.client import generate_answer, summarize_scan
from app.personalization.patient_check import check_patient_chart
from app.personalization.scorer import build_summary_content, score_familiarity
from app.retrieval.index import retrieve


router = APIRouter(prefix="/drug", tags=["drug"])

MAX_BULLETS = 3
MAX_SEARCH_RESULTS = 50


def _patient_context_block(patient: dict) -> Optional[str]:
    """
    Format the clinically-relevant fields of a patient chart for the LLM
    prompt. Deliberately narrow: age, sex, weight, allergies, and current
    medications are the fields that can actually change a dosing/interaction
    answer. Name, medical history, and free-text notes are left out.
    """
    lines: list[str] = []

    demographics = []
    if patient.get("age") is not None:
        demographics.append(f"{patient['age']}yo")
    if patient.get("sex"):
        demographics.append(str(patient["sex"]))
    if patient.get("weight_kg") is not None:
        demographics.append(f"{patient['weight_kg']}kg")
    if demographics:
        lines.append("Patient: " + ", ".join(demographics))

    allergies = str(patient.get("allergies") or "").strip()
    if allergies and allergies.lower() not in {
        "none",
        "none known",
        "nka",
        "nkda",
    }:
        lines.append(f"Allergies: {allergies}")

    current_medications = str(
        patient.get("current_medications") or ""
    ).strip()

    if (
        current_medications
        and current_medications.lower() != "none"
    ):
        lines.append(
            f"Current medications: {current_medications}"
        )

    return "\n".join(lines) if lines else None


class AskRequest(BaseModel):
    hcp_id: str = Field(max_length=64)
    query: str = Field(max_length=2000)
    conversation_id: Optional[str] = Field(
        default=None,
        max_length=64,
    )
    patient_id: Optional[str] = Field(
        default=None,
        max_length=64,
    )


@router.get("/search")
def search_drugs(
    q: str = "",
    limit: int = 25,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    """
    Name search over the full drug catalog, for the frontend's "add a
    drug" picker. Not scoped to an hcp_id — it's a lookup against the
    shared reference corpus, not personalized or owned data.
    """
    limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    query = q.strip()

    mongo_filter: dict = {}

    if query:
        mongo_filter = {
            "name": {
                "$regex": f"^{re.escape(query)}",
                "$options": "i",
            }
        }

    rows = (
        db.drugs.find(
            mongo_filter,
            {
                "_id": 1,
                "name": 1,
            },
        )
        .sort("name", 1)
        .limit(limit)
    )

    return {
        "drugs": [
            {
                "drug_id": row["_id"],
                "name": row.get("name") or row["_id"],
            }
            for row in rows
        ]
    }


@router.get("/{drug_id}/summary")
def get_summary(
    drug_id: str,
    hcp_id: str,
    patient_id: Optional[str] = None,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    """
    Personalized HUD content for a drug, tailored to the HCP's
    familiarity tier. Optional patient_id adds a chart name-match
    check from the patient folder.
    """
    assert_same_hcp(hcp, hcp_id)

    drug_id = reject_path_id(
        drug_id,
        "drug_id",
    )

    drug = db.drugs.find_one(
        {
            "_id": drug_id,
        }
    )

    if drug is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown drug_id: {drug_id}",
        )

    tier = score_familiarity(
        hcp["_id"],
        drug_id,
        db,
    )

    specialty = hcp.get("specialty") or ""

    requested = (
        patient_id or ""
    ).strip()

    headline, full_bullets = build_summary_content(
        drug_id,
        tier,
        specialty=specialty,
        compact=False,
    )

    name = drug.get(
        "name",
        drug_id,
    )

    check = None

    if requested:
        try:
            patient = owned_patient(
                db,
                hcp,
                requested,
            )

            check = check_patient_chart(
                patient,
                drug_id,
                name,
            )

        except HTTPException:
            raise

        except Exception:
            check = None

    # Always rewrite the selected dossier sections through Grok. Chart data
    # stays out of that prompt; it is only used for patient_check below.
    bullets, summary_source = summarize_scan(name, full_bullets, tier, specialty)
    if summary_source != "grok":
        bullets = []
        summary_source = "unavailable"

    return {
        "drug_id": drug["_id"],
        "name": name,
        "tier": tier,
        "headline": headline,
        "bullets": bullets,
        "summary_source": summary_source,
        "full_bullets": [],
        "patient_check": check,
    }


@router.post("/{drug_id}/ask")
def ask_question(
    drug_id: str,
    payload: AskRequest,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    """
    Personalized RAG follow-up question.

    The familiarity tier is calculated before the answer is generated,
    so repeated interactions with the same drug produce progressively
    more advanced responses.

    If patient_id is provided, the patient is verified as belonging
    to the authenticated HCP. Relevant chart information is included
    in the LLM context and the patient_id is stored with the chat.
    """
    assert_same_hcp(
        hcp,
        payload.hcp_id,
    )

    drug_id = reject_path_id(
        drug_id,
        "drug_id",
    )

    if db.drugs.find_one({"_id": drug_id}) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown drug_id: {drug_id}",
        )

    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="query must not be empty",
        )

    tier = score_familiarity(
        hcp["_id"],
        drug_id,
        db,
    )

    specialty = hcp.get("specialty") or ""

    patient_id = (
        payload.patient_id or ""
    ).strip() or None

    patient_context = None

    if patient_id:
        patient = owned_patient(
            db,
            hcp,
            patient_id,
        )

        patient_context = _patient_context_block(
            patient
        )

    try:
        context = retrieve(
            drug_id,
            query,
            specialty=specialty,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval failed: {exc}",
        )

    if not context:
        raise HTTPException(
            status_code=404,
            detail=(
                "No relevant information found "
                "for this drug."
            ),
        )

    try:
        answer = generate_answer(
            query,
            context,
            tier,
            specialty=specialty,
            patient_context=patient_context,
        )

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

    conversation_id = (
        payload.conversation_id
        or str(uuid4())
    )

    db.chats.insert_one(
        {
            "hcp_id": hcp["_id"],
            "drug_id": drug_id,
            "patient_id": patient_id,
            "conversation_id": conversation_id,
            "question": query,
            "answer": answer,
            "asked_at": datetime.now(timezone.utc),
        }
    )

    return {
        "answer_text": answer,
        "conversation_id": conversation_id,
        "patient_id": patient_id,
    }
