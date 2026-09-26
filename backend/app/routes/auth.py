"""Create-account, login, logout, and password reset for clinicians."""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

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
    public_hcp,
    valid_email,
)
from app.db.database import get_db
from app.db.passwords import (
    MAX_PASSWORD_LENGTH,
    hash_password,
    new_recovery_code,
    password_matches,
    validate_new_password,
    verify_password,
)
from app.db.resets import RESET_MINUTES, consume_open_reset, start_password_reset
from app.db.seed import DEMO_HCPS
from app.db.sessions import create_session, current_hcp, revoke_sessions, revoke_token

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("uvicorn.error")

_ATTEMPTS = {}  # type: Dict[str, Tuple[float, int]]
_ATTEMPT_WINDOW = 600.0
_ATTEMPT_LIMIT = 8
_DEMO_EMAILS = {row["email"] for row in DEMO_HCPS}


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(max_length=MAX_NAME_LENGTH)
    last_name: str = Field(max_length=MAX_NAME_LENGTH)
    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    professional_role: str = Field(max_length=MAX_FIELD_LENGTH)
    specialty: str = Field(max_length=MAX_FIELD_LENGTH)
    credentials: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)
    organization: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)
    practice_setting: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)
    work_phone: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)
    city: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)
    region: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)
    country: Optional[str] = Field(default="", max_length=MAX_FIELD_LENGTH)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    recovery_code: str = Field(max_length=32)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    reset_token: str = Field(max_length=128)
    new_password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(max_length=MAX_PASSWORD_LENGTH)


def _prune_attempts(now: float) -> None:
    stale = [key for key, (start, _) in list(_ATTEMPTS.items()) if now - start > _ATTEMPT_WINDOW]
    for key in stale:
        _ATTEMPTS.pop(key, None)


def _too_many(key: str) -> None:
    now = time.time()
    _prune_attempts(now)
    window_start, count = _ATTEMPTS.get(key, (now, 0))
    if now - window_start <= _ATTEMPT_WINDOW and count >= _ATTEMPT_LIMIT:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")


def _record_failure(key: str) -> None:
    now = time.time()
    window_start, count = _ATTEMPTS.get(key, (now, 0))
    if now - window_start > _ATTEMPT_WINDOW:
        window_start, count = now, 0
    _ATTEMPTS[key] = (window_start, count + 1)


def _clear_attempts(key: str) -> None:
    _ATTEMPTS.pop(key, None)


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
    first = optional_text(payload.first_name, MAX_NAME_LENGTH)
    last = optional_text(payload.last_name, MAX_NAME_LENGTH)
    email = normalize_email(payload.email)
    role = optional_text(payload.professional_role)
    specialty = optional_text(payload.specialty)
    _too_many("register:%s" % email)
    if not first or not last or not role or not specialty:
        raise HTTPException(status_code=422, detail="Name, role, and specialty are required.")
    if not valid_email(email):
        raise HTTPException(status_code=422, detail="Enter an email address such as name@example.com.")
    password = validate_new_password(payload.password, email)
    if db.hcps.find_one({"email": email}) is not None:
        _record_failure("register:%s" % email)
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
        "created_at": datetime.now(timezone.utc),
        "account_source": "register",
    }
    try:
        db.hcps.insert_one(row)
    except DuplicateKeyError:
        _record_failure("register:%s" % email)
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    logger.info(
        "Inserted clinician %s email=%s into %s.hcps",
        hcp_id,
        email,
        db.name,
    )
    return _auth_payload(db, row, recovery)


@router.post("/login")
def login(payload: LoginRequest, db: Database = Depends(get_db)) -> dict:
    """Verify the stored hash only. Do not run validate_new_password here."""
    email = normalize_email(payload.email)
    limit_key = "login:%s" % email
    if email not in _DEMO_EMAILS:
        _too_many(limit_key)
    hcp = db.hcps.find_one({"email": email})
    stored = (hcp or {}).get("password_hash") or ""
    if hcp is None or not password_matches(payload.password, stored):
        if email not in _DEMO_EMAILS:
            _record_failure(limit_key)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    _clear_attempts(limit_key)
    if not hcp.get("recovery_hash"):
        _issue_recovery(db, hcp["_id"])
        hcp = db.hcps.find_one({"_id": hcp["_id"]})
    return _auth_payload(db, hcp)


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
    _too_many("change:%s" % hcp["_id"])
    if not password_matches(payload.current_password, hcp.get("password_hash") or ""):
        _record_failure("change:%s" % hcp["_id"])
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
    _too_many("reset:%s" % email)
    hcp = db.hcps.find_one({"email": email})
    code = (payload.recovery_code or "").strip().upper()
    stored = (hcp or {}).get("recovery_hash") or ""
    if hcp is None or not stored or not password_matches(code, stored):
        _record_failure("reset:%s" % email)
        raise HTTPException(status_code=401, detail="Email or recovery code is incorrect.")
    ticket = start_password_reset(db, hcp["_id"])
    ticket["detail"] = "This reset expires in %s minutes and can be used only once." % RESET_MINUTES
    return ticket


@router.post("/reset-password")
def reset_password(payload: ResetRequest, db: Database = Depends(get_db)) -> dict:
    email = normalize_email(payload.email)
    _too_many("finish-reset:%s" % email)
    password = validate_new_password(payload.new_password, email)
    hcp = db.hcps.find_one({"email": email})
    try:
        ticket = consume_open_reset(db, payload.reset_token)
    except HTTPException:
        _record_failure("finish-reset:%s" % email)
        raise
    if hcp is None or ticket["hcp_id"] != hcp["_id"]:
        _record_failure("finish-reset:%s" % email)
        raise HTTPException(status_code=401, detail="This reset is no longer valid.")
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
