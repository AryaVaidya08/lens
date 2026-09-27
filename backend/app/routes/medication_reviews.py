"""Patient-scoped medication review drafts. Never modifies the clinic chart.

Comparison is deliberately literal: no inferred dose equivalence, therapeutic
substitution, or treatment advice. Clinicians confirm identity links themselves.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.accounts import reject_path_id
from app.db.database import get_db
from app.db.sessions import current_hcp

router = APIRouter(prefix="/patients/{patient_id}/medication-reviews", tags=["medication reviews"])


class MedicationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    strength: str = Field(default="", max_length=200)
    formulation: str = Field(default="", max_length=200)
    directions: str = Field(default="", max_length=1000)
    source_text: str = Field(default="", max_length=12000)
    reported_use: Literal["taking", "not_taking", "unsure", "not_asked"] = "not_asked"
    notes: str = Field(default="", max_length=2000)
    reference_id: Optional[str] = Field(default=None, max_length=64)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    revision: int = Field(default=0, ge=0)
    reference_source: str = Field(default="", max_length=500)
    reference_text: str = Field(default="", max_length=20000)
    reference_verified: bool = False
    collection_complete: bool = False
    reference: list[MedicationEntry] = Field(default_factory=list, max_length=100)
    observed: list[MedicationEntry] = Field(default_factory=list, max_length=100)
    notes: str = Field(default="", max_length=4000)
    reviewed: bool = False

    @model_validator(mode="after")
    def validate_entries(self):
        for entries in (self.reference, self.observed):
            if len({e.id for e in entries}) != len(entries):
                raise ValueError("Medication entry IDs must be unique within each list.")
        ids = {e.id for e in self.reference}
        if any(e.reference_id is not None and e.reference_id not in ids for e in self.observed):
            raise ValueError("A bottle is linked to a reference entry that no longer exists.")
        if self.reviewed and (not self.reference_source or not self.reference_verified or not self.collection_complete):
            raise ValueError("Confirm the reference list, its source, and completion of bottle collection before comparing.")
        return self


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def compare(review: ReviewInput) -> list[dict]:
    findings = []

    def add(kind, title, detail, reference_id=None, observed_id=None):
        findings.append(dict(kind=kind, title=title, detail=detail,
                             reference_id=reference_id, observed_id=observed_id))

    matched = {r.id: [] for r in review.reference}
    for bottle in review.observed:
        # Explicit links allow brand/generic names to be resolved by the HCP.
        candidates = [r for r in review.reference if r.id == bottle.reference_id] if bottle.reference_id else [
            r for r in review.reference if normalized(r.name) == normalized(bottle.name)
        ]
        if len(candidates) != 1:
            title = "Identity needs clarification" if candidates else "No reference match"
            add("identity" if candidates else "unmatched", title,
                f"{bottle.name}: confirm its identity against the reference list. An unmatched name does not establish an additional therapy.",
                observed_id=bottle.id)
        else:
            ref = candidates[0]
            matched[ref.id].append(bottle)
            for field, label in (("strength", "Strength"), ("formulation", "Formulation"), ("directions", "Directions")):
                expected, actual = getattr(ref, field), getattr(bottle, field)
                if not expected or not actual:
                    add("incomplete", f"{label} incomplete", f"{bottle.name} — reference: {expected or 'not recorded'}; bottle: {actual or 'not recorded'}.", ref.id, bottle.id)
                elif normalized(expected) != normalized(actual):
                    add("difference", f"{label} text differs", f"{bottle.name} — reference: {expected}; bottle: {actual}. Confirm whether this is a meaningful difference.", ref.id, bottle.id)
        if bottle.reported_use != "taking":
            use = {"not_taking": "Patient reports not taking", "unsure": "Patient is unsure about use", "not_asked": "Actual use has not been established"}[bottle.reported_use]
            add("reported_use", use, f"{bottle.name}. {bottle.notes}".strip(), observed_id=bottle.id)
    for ref in review.reference:
        if not matched[ref.id]:
            add("not_located", "Reference medication not matched to a bottle",
                f"{ref.name}: no confirmed bottle match in this review. This does not establish that the patient is not taking it.", ref.id)
        elif len(matched[ref.id]) > 1:
            add("multiple_bottles", "Multiple bottles linked to one reference entry",
                f"{ref.name}: {len(matched[ref.id])} bottles captured. Clarify which containers the patient uses; this is not a duplicate-therapy determination.", ref.id)
    return findings


def report_text(review: ReviewInput, findings: list[dict], patient: dict, hcp: dict, saved_at: str) -> str:
    lines = ["MEDICATION REVIEW — for clinician follow-up", f"Patient: {patient.get('first_name', '')} {patient.get('last_name', '')} ({patient['_id']})",
             f"Reviewed by: {hcp.get('name', hcp['_id'])}", f"Saved: {saved_at}", f"Reference source: {review.reference_source}"]
    for heading, entries in (("REFERENCE LIST", review.reference), ("CONFIRMED BOTTLE DETAILS", review.observed)):
        lines += ["", heading]
        if not entries:
            lines.append("No entries recorded.")
        for e in entries:
            lines.append(f"- {e.name} | strength: {e.strength or 'not recorded'} | formulation: {e.formulation or 'not recorded'} | directions: {e.directions or 'not recorded'}")
            if heading == "CONFIRMED BOTTLE DETAILS":
                lines.append(f"  Patient-reported use: {e.reported_use.replace('_', ' ')}")
            if e.notes:
                lines.append(f"  Notes: {e.notes}")
            if e.source_text:
                lines.append(f"  Source transcription (may contain OCR errors): {e.source_text}")
    lines += ["", "ITEMS FOR FOLLOW-UP"]
    lines += [f"- {f['title']}: {f['detail']}" for f in findings] or ["No differences found by literal comparison. This is not a clinical safety assessment."]
    if review.notes:
        lines += ["", "Review notes: " + review.notes]
    lines += ["", "Confirm unresolved items with the appropriate clinician. This report does not recommend medication changes or replace the clinical record."]
    return "\n".join(lines)


def owned_patient(db, patient_id, hcp):
    patient_id = reject_path_id(patient_id, "patient_id")
    patient = db.patients.find_one({"_id": patient_id, "hcp_id": hcp["_id"]})
    if patient is None:
        raise HTTPException(404, "Patient not found.")
    return patient


@router.get("")
def list_reviews(patient_id: str, hcp: dict = Depends(current_hcp), db: Database = Depends(get_db)):
    owned_patient(db, patient_id, hcp)
    rows = db.medication_reviews.find({"patient_id": patient_id, "hcp_id": hcp["_id"]}, {"_id": 0}).sort("updated_at", -1)
    return {"reviews": list(rows)}


@router.put("/{review_id}")
def save_review(patient_id: str, review_id: UUID, payload: ReviewInput,
                hcp: dict = Depends(current_hcp), db: Database = Depends(get_db)):
    patient = owned_patient(db, patient_id, hcp)
    key = f"{hcp['_id']}:{patient_id}:{review_id}"
    now = datetime.now(timezone.utc).isoformat()
    findings = compare(payload) if payload.reviewed else []
    row = payload.model_dump()
    row.update(review_id=str(review_id), patient_id=patient_id, hcp_id=hcp["_id"],
               revision=payload.revision + 1, updated_at=now, findings=findings,
               report=report_text(payload, findings, patient, hcp, now) if payload.reviewed else "")
    if payload.revision == 0:
        try:
            db.medication_reviews.insert_one({"_id": key, **row})
        except DuplicateKeyError:
            raise HTTPException(409, "This review was already saved. Reopen it from the review list before editing.")
    else:
        result = db.medication_reviews.replace_one({"_id": key, "revision": payload.revision}, {"_id": key, **row})
        if result.matched_count != 1:
            raise HTTPException(409, "A newer version exists. Reopen this review from the list before editing.")
    return row
