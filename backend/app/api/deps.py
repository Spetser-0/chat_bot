"""
app/api/deps.py
────────────────
FastAPI dependency functions for authentication, authorization,
and database sessions.

These are the ONLY way route handlers should obtain the current student.
Route handlers must never extract student identity from request body/query params.
"""
from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, AuthorizationError
from app.db.session import get_db
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    decode_session_token,
    get_student_by_id,
)


async def get_current_student(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Student:
    """
    Dependency: Verify session cookie and return the authenticated student.
    Raises AuthenticationError (401) if cookie is missing or invalid.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise AuthenticationError()

    data = decode_session_token(token)
    try:
        student_id = uuid.UUID(data["sub"])
    except (KeyError, ValueError):
        raise AuthenticationError()

    return await get_student_by_id(student_id, db)


async def get_active_student(
    student: Student = Depends(get_current_student),
) -> Student:
    """
    Dependency: Like get_current_student but also checks status=active.
    """
    if student.status != "active":
        raise AuthorizationError("الحساب غير نشط.")
    return student


async def get_developer(
    student: Student = Depends(get_current_student),
) -> Student:
    """
    Dependency: Verify the current user has developer or admin role.
    Use this on ALL Developer Dashboard endpoints.
    """
    if student.role not in ("developer", "admin"):
        raise AuthorizationError()
    return student


async def get_admin(
    student: Student = Depends(get_current_student),
) -> Student:
    """Dependency: Admin-only access."""
    if student.role != "admin":
        raise AuthorizationError()
    return student
