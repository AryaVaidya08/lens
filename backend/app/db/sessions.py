"""Opaque session tokens. The raw token is returned once; only the hash is stored."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
from pymongo.database import Database

from app.db.database import get_db
from app.db.passwords import hash_token, new_session_token

SESSION_DAYS = 14


def create_session(db: Database, hcp_id: str) -> str:
    token = new_session_token()
    now = datetime.now(timezone.utc)
    db.sessions.insert_one(
        {
            "token_hash": hash_token(token),
            "hcp_id": hcp_id,
            "created_at": now,
            "expires_at": now + timedelta(days=SESSION_DAYS),
        }
    )
    return token


def revoke_sessions(db: Database, hcp_id: str) -> None:
    db.sessions.delete_many({"hcp_id": hcp_id})


def revoke_token(db: Database, token: str) -> None:
    if token:
        db.sessions.delete_many({"token_hash": hash_token(token)})


def current_hcp(
    authorization: Optional[str] = Header(default=None),
    db: Database = Depends(get_db),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in required.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    row = db.sessions.find_one({"token_hash": hash_token(token)})
    if row is None:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    expires = row.get("expires_at")
    now = datetime.now(timezone.utc)
    if expires is not None and getattr(expires, "tzinfo", None) is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is not None and expires < now:
        db.sessions.delete_one({"_id": row["_id"]})
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    hcp = db.hcps.find_one({"_id": row["hcp_id"]})
    if hcp is None:
        db.sessions.delete_one({"_id": row["_id"]})
        raise HTTPException(status_code=401, detail="Sign in required.")
    hcp["_session_token"] = token
    return hcp


def assert_same_hcp(hcp: dict, hcp_id: str) -> None:
    if hcp_id and hcp_id != hcp["_id"]:
        raise HTTPException(status_code=403, detail="That account is not yours.")
