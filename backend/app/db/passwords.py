"""Password and recovery-code hashing. Never store plaintext secrets."""

import hashlib
import hmac
import os
import re
import secrets

from fastapi import HTTPException


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return "%s:%s" % (salt.hex(), digest.hex())


def verify_password(password: str, stored: str) -> bool:
    if not stored or ":" not in stored:
        return False
    salt_hex, digest_hex = stored.split(":", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(actual, expected)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_recovery_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


def validate_new_password(password: str, email: str = "") -> str:
    password = password or ""
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")
    if password.strip() != password or " " in password:
        raise HTTPException(status_code=422, detail="Password cannot contain spaces.")
    lowered = password.lower()
    local = (email or "").split("@")[0].lower()
    if local and local in lowered:
        raise HTTPException(status_code=422, detail="Password cannot contain your email name.")
    if lowered in {"password", "password1", "12345678", "qwertyui"}:
        raise HTTPException(status_code=422, detail="Choose a less common password.")
    return password
