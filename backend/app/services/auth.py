"""
app/services/auth.py
─────────────────────
Session-based authentication service.
Uses itsdangerous signed cookies.
Designed to be replaceable with Supabase Auth without rewriting feature services.

Key invariants:
- Never trust client-supplied student_id
- Always verify from the signed session
- Developer role checked separately from student role
"""
from __future__ import annotations

import uuid
from typing import Any

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


SESSION_COOKIE_NAME = "spetser_session"


def _get_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.session_secret_key)


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


def create_session_token(student_id: uuid.UUID, role: str) -> str:
    """Create a signed, time-limited session token."""
    serializer = _get_serializer()
    return serializer.dumps({"sub": str(student_id), "role": role})


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

    if student is None or not student.password_hash:
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
