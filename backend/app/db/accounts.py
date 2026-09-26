"""HCP document helpers — public profile shape and patient serialization."""

import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pymongo.database import Database

from app.personalization.scorer import tier_for_touch_count

# ASCII only so lookalike Unicode emails cannot impersonate another account.
_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
MAX_EMAIL_LENGTH = 254
MAX_NAME_LENGTH = 80
MAX_FIELD_LENGTH = 200

PROFILE_KEYS = (
    "first_name",
    "last_name",
    "email",
    "professional_role",
    "credentials",
    "specialty",
    "organization",
    "practice_setting",
    "work_phone",
    "city",
    "region",
    "country",
)


def display_name(first_name: str, last_name: str, professional_role: str) -> str:
    full = ("%s %s" % (first_name.strip(), last_name.strip())).strip()
    if professional_role == "Physician" or not professional_role:
        return "Dr. %s" % full if full else "Dr."
    return full


def public_hcp(hcp: Dict[str, Any], db: Database) -> Dict[str, Any]:
    engagements = list(db.engagements.find({"hcp_id": hcp["_id"]}))
    body = {
        "hcp_id": hcp["_id"],
        "name": hcp.get("name") or "",
        "specialty": hcp.get("specialty") or "",
        "familiarity": {
            row["drug_id"]: tier_for_touch_count(row["touch_count"]) for row in engagements
        },
        "patient_ids": list(hcp.get("patient_ids") or []),
    }
    for key in PROFILE_KEYS:
        if key in hcp and hcp[key] is not None:
            body[key] = hcp[key]
    return body


def public_patient(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patient_id": row["_id"],
        "hcp_id": row.get("hcp_id"),
        "first_name": row.get("first_name") or "",
        "last_name": row.get("last_name") or "",
        "birth_date": row.get("birth_date") or "",
        "age": row.get("age"),
        "weight_kg": row.get("weight_kg"),
        "sex": row.get("sex") or "",
        "medical_history": row.get("medical_history") or "",
        "allergies": row.get("allergies") or "",
        "current_medications": row.get("current_medications") or "",
        "notes": row.get("notes") or "",
        "source": row.get("source") or "",
        "external_id": row.get("external_id") or "",
    }


def require_hcp(db: Database, hcp_id: str) -> Dict[str, Any]:
    hcp = db.hcps.find_one({"_id": hcp_id})
    if hcp is None:
        raise HTTPException(status_code=404, detail="Unknown hcp_id: %s" % hcp_id)
    return hcp


def patients_for_hcp(db: Database, hcp: Dict[str, Any]) -> List[Dict[str, Any]]:
    ids = list(hcp.get("patient_ids") or [])
    if not ids:
        return []
    found = {row["_id"]: row for row in db.patients.find({"_id": {"$in": ids}})}
    return [
        public_patient(found[pid])
        for pid in ids
        if pid in found and found[pid].get("hcp_id") == hcp["_id"]
    ]


def owned_patient(db: Database, hcp: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
    patient_id = reject_path_id(patient_id, "patient_id")
    row = db.patients.find_one({"_id": patient_id})
    if row is None or row.get("hcp_id") != hcp["_id"]:
        raise HTTPException(status_code=404, detail="Unknown patient_id: %s" % patient_id)
    return row


def reject_path_id(value: str, label: str) -> str:
    text = (value or "").strip()
    if not text or ".." in text or "/" in text or "\\" in text or "\x00" in text:
        raise HTTPException(status_code=404, detail="Unknown %s: %s" % (label, value))
    return text


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    if not email or len(email) > MAX_EMAIL_LENGTH or "\x00" in email:
        return False
    return bool(_EMAIL.match(email))


def optional_text(value: Optional[str], max_length: int = MAX_FIELD_LENGTH) -> str:
    text = (value or "").strip()
    if len(text) > max_length:
        raise HTTPException(status_code=422, detail="That field is too long.")
    return text
