"""HCP profile, voice chat log, and the doctor's patient folder list."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.database import Database

from app.db.accounts import (
    display_name,
    normalize_email,
    optional_text,
    patients_for_hcp,
    public_hcp,
)
from app.db.database import get_db
from app.db.passwords import verify_password
from app.db.sessions import assert_same_hcp, current_hcp

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    current_password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    professional_role: Optional[str] = None
    specialty: Optional[str] = None
    credentials: Optional[str] = None
    organization: Optional[str] = None
    practice_setting: Optional[str] = None
    work_phone: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


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

    return {
        "chats": [
            {
                "id": str(row["_id"]),
                "drug_id": row["drug_id"],
                "question": row["question"],
                "answer": row["answer"],
                "asked_at": (
                    row["asked_at"].isoformat()
                    if row.get("asked_at")
                    else None
                ),
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

    for key, value in patch.items():
        if value is None:
            continue

        text = optional_text(value) if isinstance(value, str) else value

        if key == "email":
            email = normalize_email(text)

            if email != (hcp.get("email") or ""):
                if not verify_password(
                    current_password or "",
                    hcp.get("password_hash") or "",
                ):
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
        db.hcps.update_one(
            {"_id": hcp["_id"]},
            {"$set": updates},
        )

    updated_hcp = db.hcps.find_one({"_id": hcp["_id"]})
    return public_hcp(updated_hcp, db)