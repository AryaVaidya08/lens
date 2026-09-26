"""Password and recovery-code hashing. Never store plaintext secrets."""

import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException

MAX_PASSWORD_LENGTH = 128
_PRODUCTION_ITERATIONS = 200_000
_TEST_ITERATIONS = 2_000


def _hash_iterations() -> int:
    raw = os.environ.get("PASSWORD_HASH_ITERATIONS", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    # mongomock is pytest-only; keep the real cost on Atlas/localhost.
    if os.environ.get("MONGODB_URI", "").startswith("mongomock"):
        return _TEST_ITERATIONS
    return _PRODUCTION_ITERATIONS


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _hash_iterations()
    )
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
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _hash_iterations()
    )
    return hmac.compare_digest(actual, expected)


# Same cost as a real check so missing accounts don't fail faster than real ones.
_DUMMY_PASSWORD_HASH = hash_password("timing-pad")


def password_matches(password: str, stored: str) -> bool:
    """Verify in constant-ish time. The dummy hash is never treated as a real secret."""
    if not password or len(password) > MAX_PASSWORD_LENGTH:
        verify_password("x", _DUMMY_PASSWORD_HASH)
        return False
    if not stored:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        return False
    return verify_password(password, stored)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_recovery_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


def validate_new_password(password: str, email: str = "") -> str:
    password = password or ""
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(status_code=422, detail="Password must be at most %s characters." % MAX_PASSWORD_LENGTH)
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
