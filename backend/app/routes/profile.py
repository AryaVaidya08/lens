"""HCP profile, voice chat log, and the doctor's patient folder list."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

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
from app.db.accounts import owned_patient, public_patient

router = APIRouter(prefix="/profile", tags=["profile"])

MAX_CHART_TEXT_LENGTH = 2000


def to_utc_iso(value: Optional[datetime]) -> Optional[str]:
    """Serialize a datetime as an unambiguous UTC ISO string.

    MongoDB returns naive datetimes even though everything we write is UTC.
    A naive isoformat() string (no offset) gets parsed by JS `Date` as local
    time, not UTC, which is why times looked "stuck" on the server's clock.
    Attaching UTC tzinfo before formatting fixes that: the browser can then
    convert correctly with `new Date(value).toLocaleString()`.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


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

class RenameChatRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    last_name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    birth_date: Optional[str] = Field(default=None, max_length=10)
    age: Optional[int] = Field(default=None, ge=0, le=150)
    weight_kg: Optional[float] = Field(default=None, ge=0, le=500)
    sex: Optional[str] = Field(default=None, max_length=MAX_FIELD_LENGTH)
    medical_history: Optional[str] = Field(default=None, max_length=MAX_CHART_TEXT_LENGTH)
    allergies: Optional[str] = Field(default=None, max_length=MAX_CHART_TEXT_LENGTH)
    current_medications: Optional[str] = Field(default=None, max_length=MAX_CHART_TEXT_LENGTH)
    notes: Optional[str] = Field(default=None, max_length=MAX_CHART_TEXT_LENGTH)

@router.get("/{hcp_id}/chats")
def list_chats(
    hcp_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)

    rows = list(
        db.chats.find({"hcp_id": hcp["_id"]})
        .sort("asked_at", -1)
        .limit(50)
    )

    conversations = {}

    for row in rows:
        # New chats have conversation_id.
        # Older chats use their MongoDB ID as a stable fallback.
        conversation_id = row.get("conversation_id") or str(row["_id"])

        if conversation_id not in conversations:
            conversations[conversation_id] = []

        conversations[conversation_id].append(row)

    chats = []

    for conversation_id, conversation_rows in conversations.items():
        # Oldest message first inside the conversation.
        conversation_rows.sort(
            key=lambda row: row.get("asked_at") or datetime.min
        )

        messages = []

        for row in conversation_rows:
            row_id = str(row["_id"])

            messages.append(
                {
                    "id": f"{row_id}-user",
                    "role": "user",
                    "text": row["question"],
                }
            )

            messages.append(
                {
                    "id": f"{row_id}-assistant",
                    "role": "assistant",
                    "text": row["answer"],
                }
            )

        latest_row = conversation_rows[-1]
        first_row = conversation_rows[0]

        chats.append(
            {
                "id": conversation_id,
                "conversation_id": conversation_id,
                "drug_id": latest_row["drug_id"],
                "question": first_row["question"],
                "answer": first_row["answer"],
                "title": latest_row.get("title")
                or first_row["question"][:50],
                "preview": latest_row["question"],
                "asked_at": to_utc_iso(latest_row.get("asked_at")),
                "messages": messages,
            }
        )
    # Most recently active conversation first.
    chats.sort(key=lambda chat: chat.get("asked_at") or "", reverse=True)

    return {"chats": chats}

@router.delete("/{hcp_id}/chats/{conversation_id}")
def delete_chat(
    hcp_id: str,
    conversation_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)

    # New conversations store conversation_id directly.
    result = db.chats.delete_many(
        {
            "hcp_id": hcp["_id"],
            "conversation_id": conversation_id,
        }
    )

    # Legacy conversations did not have conversation_id.
    # Their conversation ID is represented by their MongoDB _id.
    if result.deleted_count == 0:
        from bson import ObjectId

        try:
            object_id = ObjectId(conversation_id)
        except Exception:
            object_id = None

        if object_id:
            result = db.chats.delete_many(
                {
                    "hcp_id": hcp["_id"],
                    "_id": object_id,
                }
            )

    return {
        "deleted": result.deleted_count > 0,
    }

@router.get("/{hcp_id}/patients")
def list_patients(
    hcp_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)
    return {"patients": patients_for_hcp(db, hcp)}


@router.post("/{hcp_id}/patients")
def create_patient(
    hcp_id: str,
    payload: PatientCreate,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    """Create a new patient chart directly in Mongo. The only writer of patients."""
    assert_same_hcp(hcp, hcp_id)

    first = optional_text(payload.first_name, MAX_NAME_LENGTH)
    last = optional_text(payload.last_name, MAX_NAME_LENGTH)
    if not first or not last:
        raise HTTPException(status_code=422, detail="First and last name are required.")

    patient_id = "pat_%s" % uuid4().hex[:12]
    row = {
        "_id": patient_id,
        "hcp_id": hcp["_id"],
        "external_id": "",
        "source": "manual",
        "first_name": first,
        "last_name": last,
        "birth_date": optional_text(payload.birth_date, 10),
        "age": payload.age,
        "weight_kg": payload.weight_kg,
        "sex": optional_text(payload.sex, MAX_FIELD_LENGTH),
        "medical_history": optional_text(payload.medical_history, MAX_CHART_TEXT_LENGTH),
        "allergies": optional_text(payload.allergies, MAX_CHART_TEXT_LENGTH),
        "current_medications": optional_text(payload.current_medications, MAX_CHART_TEXT_LENGTH),
        "notes": optional_text(payload.notes, MAX_CHART_TEXT_LENGTH),
    }
    db.patients.insert_one(row)
    db.hcps.update_one({"_id": hcp["_id"]}, {"$push": {"patient_ids": patient_id}})
    return {"patient": public_patient(row)}

@router.get("/{hcp_id}/patients/{patient_id}")
def get_patient(
    hcp_id: str,
    patient_id: str,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)

    patient = owned_patient(db, hcp, patient_id)

    return {"patient": public_patient(patient)}


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

                other = db.hcps.find_one(
                    {
                        "email": email,
                        "_id": {"$ne": hcp["_id"]},
                    }
                )

                if other is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="An account with that email already exists.",
                    )

                updates["email"] = email

            continue

        updates[key] = text

    first = updates.get(
        "first_name",
        hcp.get("first_name") or "",
    )
    last = updates.get(
        "last_name",
        hcp.get("last_name") or "",
    )
    role = updates.get(
        "professional_role",
        hcp.get("professional_role") or "",
    )

    if any(
        field in updates
        for field in ("first_name", "last_name", "professional_role")
    ):
        updates["name"] = display_name(first, last, role)

    if updates:
        updates["profile_updated_at"] = datetime.now(timezone.utc)
        try:
            result = db.hcps.update_one({"_id": hcp["_id"]}, {"$set": updates})
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
        if result.matched_count != 1:
            raise HTTPException(status_code=404, detail="Unknown hcp_id: %s" % hcp_id)
    stored = db.hcps.find_one({"_id": hcp["_id"]})
    if stored is None:
        raise HTTPException(status_code=404, detail="Unknown hcp_id: %s" % hcp_id)
    return public_hcp(stored, db)

@router.patch("/{hcp_id}/chats/{conversation_id}")
def rename_chat(
    hcp_id: str,
    conversation_id: str,
    payload: RenameChatRequest,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    assert_same_hcp(hcp, hcp_id)

    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Conversation title cannot be empty.",
        )

    result = db.chats.update_many(
        {
            "hcp_id": hcp["_id"],
            "conversation_id": conversation_id,
        },
        {
            "$set": {
                "title": title,
            }
        },
    )

    # Support old conversations that use the MongoDB _id as their conversation ID.
    if result.matched_count == 0:
        from bson import ObjectId

        try:
            object_id = ObjectId(conversation_id)
        except Exception:
            object_id = None

        if object_id:
            result = db.chats.update_one(
                {
                    "hcp_id": hcp["_id"],
                    "_id": object_id,
                },
                {
                    "$set": {
                        "title": title,
                    }
                },
            )

    return {
        "title": title,
    }