"""
app/core/security.py
────────────────────
Security utilities: password hashing, JWT tokens, secret encryption,
API key masking, and webhook signature verification.

Design decisions:
- bcrypt is used directly (passlib is unmaintained and breaks with
  bcrypt>=4.1 / Python 3.13 in the venv).
- JWT tokens are signed with HS256 using APP_SECRET_KEY.
- Fernet (AES-128-CBC + HMAC) encrypts provider API keys at rest.
  The key comes ONLY from the LLM_MASTER_ENCRYPTION_KEY environment
  variable — never hardcoded.
- Webhook signatures use HMAC-SHA512 and constant-time comparison.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.errors import AuthenticationError, SessionExpiredError

# ───────────────────────────────────────────────────────────────────────────
# Password hashing (bcrypt, direct)
# ───────────────────────────────────────────────────────────────────────────

_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt.

    Raises ValueError for empty input or passwords exceeding 72 UTF-8 bytes.
    """
    if not plain:
        raise ValueError("Password must not be empty")
    encoded = plain.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Returns False (never raises) for malformed input.
    """
    if not plain or not hashed:
        return False
    try:
        encoded = plain.encode("utf-8")
        if len(encoded) > _BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ───────────────────────────────────────────────────────────────────────────
# JWT tokens
# ───────────────────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    *,
    role: str = "student",
    is_premium: bool = False,
    expires_delta_seconds: int | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: Unique subject (e.g. student UUID as string).
        role: Role claim ("student", "developer", "admin", "superadmin").
        is_premium: Premium subscription flag.
        expires_delta_seconds: Optional override for token lifetime.
    """
    settings = get_settings()
    ttl = (
        expires_delta_seconds
        if expires_delta_seconds is not None
        else settings.access_token_expire_minutes * 60
    )
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "premium": is_premium,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a signed JWT refresh token with a longer lifetime."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT (access or refresh).

    Raises:
        AuthenticationError: token is malformed, has wrong type, or bad signature.
        SessionExpiredError: token is expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=[_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise SessionExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError() from exc
    return payload


def is_access_token(token: str) -> bool:
    """Return True if the token decodes as a valid access token."""
    try:
        return decode_token(token).get("type") == "access"
    except (AuthenticationError, SessionExpiredError):
        return False


# ───────────────────────────────────────────────────────────────────────────
# Secret encryption (Fernet) for provider API keys at rest
# ───────────────────────────────────────────────────────────────────────────


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.llm_master_encryption_key
    if not key:
        raise ValueError(
            "LLM_MASTER_ENCRYPTION_KEY is required for encrypting/decrypting "
            "secrets. Set it in the environment (generate with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key())\")"
        )
    return Fernet(key.encode("utf-8"))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string and return the Fernet token (base64)."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted: str) -> str:
    """Decrypt a Fernet token back to the original plaintext string."""
    return _get_fernet().decrypt(encrypted.encode("utf-8")).decode("utf-8")


# ───────────────────────────────────────────────────────────────────────────
# API key masking (safe display value)
# ───────────────────────────────────────────────────────────────────────────


def mask_api_key(key: str) -> str:
    """Return a masked version of an API key for display (sk-***abcd).

    Short keys are fully masked. Never returns the full key.
    """
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:3]}***{key[-4:]}"


# ───────────────────────────────────────────────────────────────────────────
# Webhook signature verification (HMAC-SHA512, constant-time)
# ───────────────────────────────────────────────────────────────────────────


def compute_signature(payload: bytes, secret: str) -> str:
    """Compute the expected HMAC-SHA512 hex digest for a payload."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha512).hexdigest()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA512 signature using constant-time comparison.

    Returns False for empty signatures instead of raising.
    """
    if not signature or not secret:
        return False
    expected = compute_signature(payload, secret)
    return hmac.compare_digest(expected, signature)
