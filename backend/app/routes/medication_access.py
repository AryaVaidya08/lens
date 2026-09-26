"""Patient-scoped PA preparation. No payer submission or coverage determination."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.database import get_db
from app.db.sessions import current_hcp
from app.routes.medication_reviews import owned_patient

router = APIRouter(tags=["medication access"])

# A dated, deliberately narrow snapshot; never inferred from a payer name alone.
# The official page does not state an effective date for this section.
POLICY = {
    "id": "ohca-rivaroxaban-2026-09-26", "title": "SoonerCare · generic rivaroxaban tablets",
    "payer": "Oklahoma SoonerCare", "medication": "rivaroxaban",
    "strengths": ["10 mg", "15 mg", "20 mg"], "formulation": "tablet",
    "source_url": "https://oklahoma.gov/ohca/providers/types/pharmacy/prior-authorization/2026/cardiovascular.html",
    "source_date": "Retrieved 2026-09-26; effective date not stated",
    "scope": "Generic 10, 15, or 20 mg tablets requested instead of brand Xarelto. Confirm current policy and member applicability with the payer.",
    "requirements": [{"id": "brand_exception", "title": "Reason brand Xarelto cannot be used",
                      "detail": "Document the patient-specific, clinically significant reason for requesting generic rivaroxaban instead of the preferred brand."}],
}


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Requirement(InputModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    detail: str = Field(default="", max_length=3000)


class Evidence(InputModel):
    requirement_id: str = Field(min_length=1, max_length=80)
    text: str = Field(default="", max_length=6000)
    source: str = Field(default="", max_length=1000)
    confirmed: bool = False


class AccessInput(InputModel):
    revision: int = Field(default=0, ge=0)
    policy_id: str = Field(default="", max_length=100)
    policy_title: str = Field(default="", max_length=300)
    policy_source: str = Field(default="", max_length=2000)
    policy_date: str = Field(default="", max_length=100)
    requirements: list[Requirement] = Field(default_factory=list, max_length=30)
    policy_confirmed: bool = False
    medication: str = Field(default="", max_length=200)
    strength: str = Field(default="", max_length=100)
    formulation: str = Field(default="", max_length=100)
    directions: str = Field(default="", max_length=1000)
    medication_source: str = Field(default="", max_length=12000)
    quantity: str = Field(default="", max_length=100)
    indication: str = Field(default="", max_length=2000)
    payer: str = Field(default="", max_length=200)
    plan: str = Field(default="", max_length=300)
    member_id: str = Field(default="", max_length=100)
    patient_dob: str = Field(default="", max_length=100)
    prescriber: str = Field(default="", max_length=300)
    prescriber_contact: str = Field(default="", max_length=500)
    rationale: str = Field(default="", max_length=12000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=30)
    request_kind: Literal["initial", "appeal"] = "initial"
    denial_reason: str = Field(default="", max_length=6000)
    denial_reference: str = Field(default="", max_length=1000)
    # Accommodate a generated letter containing all 30 bounded evidence entries,
    # so a valid saved draft can always be submitted again without a 422.
    letter: str = Field(default="", max_length=300000)
    reviewed: bool = False
    status: Literal["incomplete", "ready", "submitted", "approved", "denied", "obtained"] = "incomplete"
    status_note: str = Field(default="", max_length=3000)
    assignee: str = Field(default="", max_length=300)
    follow_up: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def unique_ids(self):
        for ids in ([r.id for r in self.requirements], [e.requirement_id for e in self.evidence]):
            if len(ids) != len(set(ids)):
                raise ValueError("Requirement and evidence IDs must be unique.")
        return self


def resolve_policy(payload):
    if payload.policy_id == POLICY["id"]:
        return POLICY
    if payload.policy_id == "custom":
        return dict(id="custom", title=payload.policy_title, payer=payload.payer,
                    medication=payload.medication, strengths=[], formulation=payload.formulation,
                    source_url=payload.policy_source, source_date=payload.policy_date,
                    scope="Staff-entered policy checklist. Verify against the current payer source.",
                    requirements=[r.model_dump() for r in payload.requirements])
    if payload.policy_id:
        raise HTTPException(422, "Unknown policy. Select a supported policy or enter the payer's requirements.")
    return None


def assess(payload):
    """Checks documentation presence and attestations, never clinical eligibility."""
    policy = resolve_policy(payload)
    missing = []
    fields = [("medication", "Medication"), ("strength", "Strength"), ("formulation", "Formulation"),
              ("directions", "Prescribed directions"), ("quantity", "Quantity and days' supply"),
              ("indication", "Indication"), ("payer", "Payer"), ("plan", "Exact plan"),
              ("member_id", "Member ID"), ("patient_dob", "Patient date of birth"),
              ("prescriber", "Prescriber name / NPI"), ("prescriber_contact", "Prescriber contact"),
              ("rationale", "Patient-specific clinical rationale")]
    missing += [label for field, label in fields if not getattr(payload, field)]
    if policy is None:
        missing.append("Select a policy or enter sourced payer requirements")
    else:
        if not all((policy["title"], policy["source_url"], policy["source_date"], policy["requirements"])):
            missing.append("Policy title, source, date/version, and at least one requirement")
        if policy["id"] != "custom":
            normalize = lambda s: " ".join(s.casefold().split())
            if (normalize(payload.medication) != policy["medication"]
                    or normalize(payload.strength).replace(" ", "") not in {s.replace(" ", "") for s in policy["strengths"]}
                    or normalize(payload.formulation) not in {"tablet", "tablets"}
                    or normalize(payload.payer) != normalize(policy["payer"])):
                missing.append("Selected policy does not match this drug, strength, formulation, or payer")
        evidence = {e.requirement_id: e for e in payload.evidence}
        allowed = {r["id"] for r in policy["requirements"]}
        if set(evidence) - allowed:
            raise HTTPException(422, "Evidence refers to a requirement outside the selected policy.")
        for r in policy["requirements"]:
            e = evidence.get(r["id"])
            if e is None or not (e.text and e.source and e.confirmed):
                missing.append(r["title"] + " — evidence, source, and review required")
    if not payload.policy_confirmed:
        missing.append("Confirm current policy applies to this patient's plan and request")
    if payload.request_kind == "appeal":
        if not payload.denial_reason:
            missing.append("Denial reason")
        if not payload.denial_reference:
            missing.append("Denial notice date / reference and appeal instructions")
    return policy, missing


def draft_letter(p, patient, policy):
    def value(s):
        return s or "[MISSING — complete before submission]"
    lines = ["DRAFT — for prescriber review", "Prior authorization appeal" if p.request_kind == "appeal" else "Prior authorization request",
             f"To: {value(p.payer)} / {value(p.plan)}",
             f"Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}; DOB: {value(p.patient_dob)}",
             f"Member ID: {value(p.member_id)}", f"Prescriber: {value(p.prescriber)}; {value(p.prescriber_contact)}",
             "", f"Requested medication: {value(p.medication)} {value(p.strength)} {value(p.formulation)}",
             f"Directions: {value(p.directions)}", f"Quantity / days' supply: {value(p.quantity)}",
             f"Indication: {value(p.indication)}", "", "Patient-specific rationale:", value(p.rationale)]
    if p.request_kind == "appeal":
        lines += ["", "Denial being appealed:", value(p.denial_reason), value(p.denial_reference)]
    if policy:
        lines += ["", f"Policy reference: {policy['title']}", policy["source_url"], policy["source_date"]]
        by_id = {e.requirement_id: e for e in p.evidence}
        for r in policy["requirements"]:
            e = by_id.get(r["id"])
            lines += ["", r["title"], value(e.text if e else ""),
                      "Evidence source: " + value(e.source if e else ""),
                      "Evidence reviewed: " + ("Yes" if e and e.confirmed else "No")]
    lines += ["", "Please review this request and the supporting records.", "Prescriber signature / date: ____________________"]
    return "\n".join(lines)


def checklist(p, missing):
    items = ["Resolve: " + item for item in missing]
    items += ["Verify member eligibility, current policy, and the correct payer form / submission route.",
              "Transfer the reviewed information into the payer's required form or portal.",
              "Attach the records referenced in each evidence entry; Lens stores references, not attachments.",
              "Obtain the prescriber's review and signature where required."]
    if p.request_kind == "appeal":
        items.append("Include the denial notice and verify the appeal deadline and delivery instructions.")
    items += ["Submit through the payer's channel and record the confirmation / reference number.",
              "Follow up on the decision, then confirm the patient obtained the medication."]
    return items


def document_content(p):
    # Workflow metadata can change without changing the clinical packet.
    return p.model_dump(exclude={"revision", "status", "status_note", "assignee", "follow_up", "reviewed"})


TRANSITIONS = {
    "incomplete": {"incomplete", "ready"}, "ready": {"incomplete", "ready", "submitted"},
    "submitted": {"incomplete", "submitted", "approved", "denied"},
    "approved": {"incomplete", "approved", "obtained"}, "denied": {"incomplete", "denied"},
    "obtained": {"incomplete", "obtained"},
}


@router.get("/medication-access/policies")
def policies(hcp: dict = Depends(current_hcp)):
    return {"policies": [POLICY]}


@router.get("/patients/{patient_id}/medication-access")
def list_cases(patient_id: str, hcp: dict = Depends(current_hcp), db: Database = Depends(get_db)):
    owned_patient(db, patient_id, hcp)
    rows = db.medication_access.find({"hcp_id": hcp["_id"], "patient_id": patient_id}, {"_id": 0}).sort("updated_at", -1)
    return {"cases": list(rows)}


@router.put("/patients/{patient_id}/medication-access/{case_id}")
def save_case(patient_id: str, case_id: UUID, payload: AccessInput,
              hcp: dict = Depends(current_hcp), db: Database = Depends(get_db)):
    patient = owned_patient(db, patient_id, hcp)
    key = f"{hcp['_id']}:{patient_id}:{case_id}"
    previous = db.medication_access.find_one({"_id": key})
    if payload.revision != (previous["revision"] if previous else 0):
        raise HTTPException(409, "A newer version exists. Reopen this case before editing.")
    previous_status = previous["status"] if previous else "incomplete"
    if payload.status not in TRANSITIONS[previous_status]:
        raise HTTPException(422, "Invalid status change. Reopen as incomplete to prepare a new request or appeal.")
    if previous:
        old_input = AccessInput(**{k: previous[k] for k in AccessInput.model_fields})
        if previous_status in {"submitted", "approved", "denied", "obtained"} and payload.status != "incomplete":
            if document_content(old_input) != document_content(payload) or old_input.reviewed != payload.reviewed:
                raise HTTPException(422, "Reopen as incomplete before editing a submitted packet.")
        old_source = document_content(old_input)
        new_source = document_content(payload)
        old_source.pop("letter")
        new_source.pop("letter")
        if old_source != new_source and payload.letter == old_input.letter:
            # An older client must not silently reuse a letter after facts change.
            payload.letter = ""
            payload.reviewed = False
    policy, missing = assess(payload)
    generated = draft_letter(payload, patient, policy)
    letter = payload.letter or generated
    if payload.status in {"ready", "submitted"} and (missing or not payload.reviewed or not payload.letter):
        raise HTTPException(422, "Complete the documentation and review the saved letter before marking ready or submitted.")
    changed_status = payload.status != previous_status
    if changed_status and payload.status in {"submitted", "approved", "denied", "obtained"} and not payload.status_note:
        raise HTTPException(422, "Record the submission reference, payer decision, or patient receipt confirmation.")
    now = datetime.now(timezone.utc).isoformat()
    history = list(previous["history"]) if previous else []
    if previous is None or changed_status:
        event = dict(status=payload.status, at=now, note=payload.status_note, actor_id=hcp["_id"])
        if payload.status == "submitted":
            event["packet"] = letter
            event["document"] = document_content(payload)
            event["policy"] = policy
        history.append(event)
    row = payload.model_dump()
    row.update(letter=letter, reviewed=payload.reviewed if payload.letter else False)
    row.update(case_id=str(case_id), patient_id=patient_id, hcp_id=hcp["_id"], revision=payload.revision + 1,
               updated_at=now, policy=policy, missing=missing, generated_letter=generated,
               checklist=checklist(payload, missing), history=history)
    if previous is None:
        try:
            db.medication_access.insert_one({"_id": key, **row})
        except DuplicateKeyError:
            raise HTTPException(409, "This case was already saved. Reopen it before editing.")
    else:
        result = db.medication_access.replace_one({"_id": key, "revision": payload.revision}, {"_id": key, **row})
        if result.matched_count != 1:
            raise HTTPException(409, "A newer version exists. Reopen this case before editing.")
    return row
