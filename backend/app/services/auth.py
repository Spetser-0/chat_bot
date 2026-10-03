"""
app/services/auth.py
─────────────────────
Session-based authentication service (local implementation).
Uses itsdangerous signed cookies.

Implements the AuthProvider protocol for abstraction.
Designed to be replaceable with Supabase Auth without rewriting feature services.

Key invariants:
- Never trust client-supplied student_id
- Always verify from the signed session
- Developer role checked separately from student role
"""
from __future__ import annotations

import os
import uuid

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    SessionExpiredError,
)
from app.models.student import Student
from app.services.auth_abstraction import (
    AuthIdentity,
    AuthProvider,
    TokenInvalidError,
)

SESSION_COOKIE_NAME = "spetser_session"
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"invalid-login-password", bcrypt.gensalt()).decode("utf-8")


def _get_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.session_secret_key)


def hash_password(plain: str) -> str:
    if len(plain.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        if len(plain.encode("utf-8")) > 72:
            return False
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_session_token(student_id: uuid.UUID, role: str, session_version: int = 1) -> str:
    """Create a signed, time-limited session token."""
    serializer = _get_serializer()
    return serializer.dumps({"sub": str(student_id), "role": role, "sv": session_version})


def decode_session_token(token: str) -> dict[str, str]:
    """
    Decode and verify session token.
    Raises AuthenticationError or SessionExpiredError on failure.
    """
    settings = get_settings()
    serializer = _get_serializer()
    try:
        data = serializer.loads(token, max_age=settings.session_max_age_seconds)
        return data
    except SignatureExpired:
        raise SessionExpiredError()
    except BadSignature:
        raise AuthenticationError()


async def authenticate_student(
    email: str, password: str, db: AsyncSession
) -> Student:
    """
    Verify credentials and return the authenticated student.
    Raises AuthenticationError with a generic message on any failure
    to avoid user enumeration.
    """
    result = await db.execute(
        select(Student).where(Student.email == email.lower().strip())
    )
    student = result.scalar_one_or_none()

    # Always run bcrypt, including for unknown emails, to prevent timing-based
    # account enumeration.
    if student is None or not student.password_hash:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise AuthenticationError("البريد الإلكتروني أو كلمة المرور غير صحيحة.")

    if not verify_password(password, student.password_hash):
        raise AuthenticationError("البريد الإلكتروني أو كلمة المرور غير صحيحة.")

    if student.status != "active":
        raise AuthorizationError("الحساب موقوف أو معلق. يرجى التواصل مع الدعم.")

    return student


async def get_student_by_id(
    student_id: uuid.UUID, db: AsyncSession
) -> Student:
    """Load a student by PK — for use after token verification only."""
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise AuthenticationError()
    return student


# ──────────────────────────────────────────────────────────────────────────────
# AuthProvider Implementation (Local Session Auth)
# ──────────────────────────────────────────────────────────────────────────────

class LocalAuthProvider:
    """
    Local session-based authentication provider.
    Implements the AuthProvider protocol for abstraction.
    """

    async def verify_credentials(
        self,
        *,
        email: str,
        password: str,
    ) -> AuthIdentity:
        # This requires a DB session; in practice we'd use a service method
        # For now, this is a placeholder — the actual verification happens
        # in authenticate_student which takes a db session
        raise NotImplementedError("Use authenticate_student service with DB session")

    async def verify_token(self, token: str) -> AuthIdentity:
        data = decode_session_token(token)
        try:
            student_id = uuid.UUID(data["sub"])
            role = data["role"]
        except (KeyError, ValueError):
            raise TokenInvalidError()
        return AuthIdentity(student_id=student_id, role=role)

    async def create_session(self, identity: AuthIdentity) -> str:
        return create_session_token(identity.student_id, identity.role)

    async def revoke_session(self, token: str) -> None:
        # With stateless signed cookies, revocation requires a blocklist
        # or short expiry. For now, we rely on short session_max_age.
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Development Authentication Mode
# ──────────────────────────────────────────────────────────────────────────────

class DevAuthProvider:
    """
    Development-only authentication provider.
    
    WARNING: Only enabled when APP_ENV=development.
    Allows authentication without real credentials for local testing.
    
    Usage:
        - Set DEV_AUTH_ENABLED=true in .env (development only)
        - Set DEV_AUTH_STUDENT_ID to a valid student UUID
        - Requests with X-Dev-Auth header will authenticate as that student
    """

    def __init__(self):
        self._enabled = False
        self._student_id: uuid.UUID | None = None
        self._configure()

    def _configure(self) -> None:
        settings = get_settings()
        # Only allow in development
        if settings.is_development:
            enabled = os.getenv("DEV_AUTH_ENABLED", "false").lower() == "true"
            student_id_str = os.getenv("DEV_AUTH_STUDENT_ID")
            if enabled and student_id_str:
                try:
                    self._student_id = uuid.UUID(student_id_str)
                    self._enabled = True
                except ValueError:
                    pass

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def get_dev_identity(self) -> AuthIdentity | None:
        if not self._enabled or not self._student_id:
            return None
        return AuthIdentity(
            student_id=self._student_id,
            role="student",
            email="dev@local.test",
            display_name="Development User",
        )


# Singleton instance
_dev_auth_provider = DevAuthProvider()


def get_dev_auth_provider() -> DevAuthProvider:
    return _dev_auth_provider


def is_dev_auth_enabled() -> bool:
    # Never allow the dev auth bypass outside local development.
    from app.core.config import get_settings
    if get_settings().app_env != "development":
        return False
    return _dev_auth_provider.is_enabled


async def get_dev_student_identity() -> AuthIdentity | None:
    """Get development auth identity if enabled, else None."""
    return _dev_auth_provider.get_dev_identity()


# ──────────────────────────────────────────────────────────────────────────────
# AuthProvider Factory (for future Supabase Auth integration)
# ──────────────────────────────────────────────────────────────────────────────

def get_auth_provider() -> AuthProvider:
    """
    Factory returning the configured AuthProvider implementation.
    
    Currently returns LocalAuthProvider.
    Future: can return SupabaseAuthProvider based on config.
    """
    return LocalAuthProvider()
