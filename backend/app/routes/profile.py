"""HCP profile, voice chat log, and the doctor's patient folder list."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.accounts import (
    MAX_EMAIL_LENGTH,
    MAX_FIELD_LENGTH,
    MAX_NAME_LENGTH,
    display_name,
    normalize_email,
    optional_text,
    patients_for_hcp,
    public_hcp,
    valid_email,
)
from app.db.database import get_db
from app.db.passwords import MAX_PASSWORD_LENGTH, password_matches
from app.db.sessions import assert_same_hcp, current_hcp

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: Optional[str] = Field(default=None, max_length=MAX_PASSWORD_LENGTH)
    first_name: Optional[str] = Field(default=None, max_length=MAX_NAME_LENGTH)
    last_name: Optional[str] = Field(default=None, max_length=MAX_NAME_LENGTH)
    email: Optional[str] = Field(default=None, max_length=MAX_EMAIL_LENGTH)
    professional_role: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    specialty: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    credentials: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    organization: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    practice_setting: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    work_phone: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    city: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    region: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    country: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)


@router.get("/{hcp_id}/chats")
def list_chats(
    hcp_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)
    rows = list(db.chats.find({"hcp_id": hcp["_id"]}).sort("asked_at", -1).limit(50))
    return {
        "chats": [
            {
                "id": str(row["_id"]),
                "drug_id": row["drug_id"],
                "question": row["question"],
                "answer": row["answer"],
                "asked_at": row["asked_at"].isoformat() if row.get("asked_at") else None,
            }
            for row in rows
        ]
    }


@router.get("/{hcp_id}/patients")
def list_patients(
    hcp_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)
    return {"patients": patients_for_hcp(db, hcp)}


@router.get("/{hcp_id}")
def get_profile(
    hcp_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)
    return public_hcp(hcp, db)


@router.patch("/{hcp_id}")
def update_profile(
    hcp_id: str,
    payload: ProfileUpdate,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)
    patch = payload.model_dump(exclude_unset=True)
    current_password = patch.pop("current_password", None)
    updates = {}
    required = {"first_name", "last_name", "professional_role", "specialty"}
    for key, value in patch.items():
        if value is None:
            continue
        if key in {"first_name", "last_name"}:
            limit = MAX_NAME_LENGTH
        elif key == "email":
            limit = MAX_EMAIL_LENGTH
        else:
            limit = MAX_FIELD_LENGTH
        text = optional_text(value, limit) if isinstance(value, str) else value
        if key in required and not text:
            raise HTTPException(status_code=422, detail="Name, role, and specialty are required.")
        if key == "email":
            email = normalize_email(text)
            if not valid_email(email):
                raise HTTPException(
                    status_code=422,
                    detail="Enter an email address such as name@example.com.",
                )
            if email != (hcp.get("email") or ""):
                if not password_matches(current_password or "", hcp.get("password_hash") or ""):
                    raise HTTPException(
                        status_code=401,
                        detail="Current password is required to change email.",
                    )
                other = db.hcps.find_one({"email": email, "_id": {"$ne": hcp["_id"]}})
                if other is not None:
                    raise HTTPException(status_code=409, detail="An account with that email already exists.")
                updates["email"] = email
            continue
        updates[key] = text

    first = updates.get("first_name", hcp.get("first_name") or "")
    last = updates.get("last_name", hcp.get("last_name") or "")
    role = updates.get("professional_role", hcp.get("professional_role") or "")
    if "first_name" in updates or "last_name" in updates or "professional_role" in updates:
        updates["name"] = display_name(first, last, role)
    if updates:
        try:
            db.hcps.update_one({"_id": hcp["_id"]}, {"$set": updates})
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
    return public_hcp(db.hcps.find_one({"_id": hcp["_id"]}), db)
