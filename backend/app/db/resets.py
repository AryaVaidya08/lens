"""One-time password-reset tickets. Valid for 15 minutes and a single use."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.database import Database

from app.db.passwords import hash_token, new_session_token

RESET_MINUTES = 15


def _aware(value):
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def start_password_reset(db: Database, hcp_id: str) -> dict:
    token = new_session_token()
    now = datetime.now(timezone.utc)
    db.password_resets.update_many(
        {"hcp_id": hcp_id, "used_at": None},
        {"$set": {"used_at": now, "superseded": True}},
    )
    db.password_resets.insert_one(
        {
            "token_hash": hash_token(token),
            "hcp_id": hcp_id,
            "created_at": now,
            "expires_at": now + timedelta(minutes=RESET_MINUTES),
            "used_at": None,
        }
    )
    return {"reset_token": token, "expires_in": RESET_MINUTES * 60}


def require_open_reset(db: Database, token: str) -> dict:
    now = datetime.now(timezone.utc)
    if not token:
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
    row = db.password_resets.find_one({"token_hash": hash_token(token)})
    if row is None:
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
    if row.get("used_at") is not None:
        raise HTTPException(status_code=401, detail="This reset was already used.")
    expires = _aware(row.get("expires_at"))
    if expires is None or expires < now:
        raise HTTPException(status_code=401, detail="This reset expired after 15 minutes.")
    return row


def consume_open_reset(db: Database, token: str) -> dict:
    """Mark a ticket used in the same query that finds it so two requests cannot both succeed."""
    now = datetime.now(timezone.utc)
    token = (token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
    digest = hash_token(token)
    row = db.password_resets.find_one_and_update(
        {"token_hash": digest, "used_at": None, "expires_at": {"$gt": now}},
        {"$set": {"used_at": now}},
        return_document=ReturnDocument.BEFORE,
    )
    if row is not None:
        return row
    existing = db.password_resets.find_one({"token_hash": digest})
    if existing is None:
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
    if existing.get("used_at") is not None:
        raise HTTPException(status_code=401, detail="This reset was already used.")
    raise HTTPException(status_code=401, detail="This reset expired after 15 minutes.")


def mark_reset_used(db: Database, row: dict) -> None:
    db.password_resets.update_one(
        {"_id": row["_id"]},
        {"$set": {"used_at": datetime.now(timezone.utc)}},
    )
