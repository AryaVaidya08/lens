"""Create-account, login, logout, and password reset for clinicians."""

import re
import time
import uuid
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.db.accounts import display_name, normalize_email, optional_text, public_hcp
from app.db.database import get_db
from app.db.passwords import (
    hash_password,
    new_recovery_code,
    validate_new_password,
    verify_password,
)
from app.db.resets import RESET_MINUTES, mark_reset_used, require_open_reset, start_password_reset
from app.db.sessions import create_session, current_hcp, revoke_sessions, revoke_token

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_ATTEMPTS = {}  # type: Dict[str, Tuple[float, int]]
_ATTEMPT_WINDOW = 600.0
_ATTEMPT_LIMIT = 8


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    professional_role: str
    specialty: str
    credentials: Optional[str] = ""
    organization: Optional[str] = ""
    practice_setting: Optional[str] = ""
    work_phone: Optional[str] = ""
    city: Optional[str] = ""
    region: Optional[str] = ""
    country: Optional[str] = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str
    recovery_code: str


class ResetRequest(BaseModel):
    email: str
    reset_token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def _valid_email(email: str) -> bool:
    return bool(_EMAIL.match(email))


def _rate_limit(key: str) -> None:
    now = time.time()
    window_start, count = _ATTEMPTS.get(key, (now, 0))
    if now - window_start > _ATTEMPT_WINDOW:
        window_start, count = now, 0
    count += 1
    _ATTEMPTS[key] = (window_start, count)
    if count > _ATTEMPT_LIMIT:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")


def _auth_payload(db: Database, hcp: dict, recovery_code: Optional[str] = None) -> dict:
    body = public_hcp(hcp, db)
    body["session_token"] = create_session(db, hcp["_id"])
    if recovery_code:
        body["recovery_code"] = recovery_code
    return body


def _issue_recovery(db: Database, hcp_id: str) -> str:
    code = new_recovery_code()
    db.hcps.update_one({"_id": hcp_id}, {"$set": {"recovery_hash": hash_password(code)}})
    return code


@router.post("/register")
def register(payload: RegisterRequest, db: Database = Depends(get_db)) -> dict:
    first = optional_text(payload.first_name)
    last = optional_text(payload.last_name)
    email = normalize_email(payload.email)
    role = optional_text(payload.professional_role)
    specialty = optional_text(payload.specialty)
    if not first or not last or not role or not specialty:
        raise HTTPException(status_code=422, detail="Name, role, and specialty are required.")
    if not _valid_email(email):
        raise HTTPException(status_code=422, detail="Enter an email address such as name@example.com.")
    password = validate_new_password(payload.password, email)
    if db.hcps.find_one({"email": email}) is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    hcp_id = "hcp_%s" % uuid.uuid4().hex[:10]
    recovery = new_recovery_code()
    row = {
        "_id": hcp_id,
        "name": display_name(first, last, role),
        "first_name": first,
        "last_name": last,
        "email": email,
        "password_hash": hash_password(password),
        "recovery_hash": hash_password(recovery),
        "professional_role": role,
        "credentials": optional_text(payload.credentials),
        "specialty": specialty,
        "organization": optional_text(payload.organization),
        "practice_setting": optional_text(payload.practice_setting),
        "work_phone": optional_text(payload.work_phone),
        "city": optional_text(payload.city),
        "region": optional_text(payload.region),
        "country": optional_text(payload.country),
        "patient_ids": [],
    }
    db.hcps.insert_one(row)
    return _auth_payload(db, row, recovery)


@router.post("/login")
def login(payload: LoginRequest, db: Database = Depends(get_db)) -> dict:
    email = normalize_email(payload.email)
    hcp = db.hcps.find_one({"email": email})
    if hcp is None or not verify_password(payload.password, hcp.get("password_hash") or ""):
        _rate_limit("login:%s" % email)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    recovery = None
    if not hcp.get("recovery_hash"):
        recovery = _issue_recovery(db, hcp["_id"])
        hcp = db.hcps.find_one({"_id": hcp["_id"]})
    return _auth_payload(db, hcp, recovery)


@router.post("/logout")
def logout(hcp: dict = Depends(current_hcp), db: Database = Depends(get_db)) -> dict:
    revoke_token(db, hcp.get("_session_token") or "")
    return {"ok": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    hcp: dict = Depends(current_hcp),
    db: Database = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, hcp.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    password = validate_new_password(payload.new_password, hcp.get("email") or "")
    if verify_password(password, hcp.get("password_hash") or ""):
        raise HTTPException(status_code=422, detail="New password must be different.")
    recovery = new_recovery_code()
    db.hcps.update_one(
        {"_id": hcp["_id"]},
        {
            "$set": {
                "password_hash": hash_password(password),
                "recovery_hash": hash_password(recovery),
            }
        },
    )
    revoke_sessions(db, hcp["_id"])
    fresh = db.hcps.find_one({"_id": hcp["_id"]})
    return _auth_payload(db, fresh, recovery)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Database = Depends(get_db)) -> dict:
    """Start a 15-minute, single-use reset after the recovery code checks out."""
    email = normalize_email(payload.email)
    hcp = db.hcps.find_one({"email": email})
    code = (payload.recovery_code or "").strip().upper()
    if (
        hcp is None
        or not hcp.get("recovery_hash")
        or not verify_password(code, hcp.get("recovery_hash") or "")
    ):
        _rate_limit("reset:%s" % email)
        raise HTTPException(status_code=401, detail="Email or recovery code is incorrect.")
    ticket = start_password_reset(db, hcp["_id"])
    ticket["detail"] = "This reset expires in %s minutes and can be used only once." % RESET_MINUTES
    return ticket


@router.post("/reset-password")
def reset_password(payload: ResetRequest, db: Database = Depends(get_db)) -> dict:
    email = normalize_email(payload.email)
    hcp = db.hcps.find_one({"email": email})
    if hcp is None:
        _rate_limit("reset:%s" % email)
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
    ticket = require_open_reset(db, payload.reset_token)
    if ticket["hcp_id"] != hcp["_id"]:
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
    password = validate_new_password(payload.new_password, email)
    mark_reset_used(db, ticket)
    recovery = new_recovery_code()
    db.hcps.update_one(
        {"_id": hcp["_id"]},
        {
            "$set": {
                "password_hash": hash_password(password),
                "recovery_hash": hash_password(recovery),
            }
        },
    )
    revoke_sessions(db, hcp["_id"])
    return {
        "ok": True,
        "recovery_code": recovery,
        "detail": "Password updated. Save the new recovery code. Sign in with your new password.",
    }
