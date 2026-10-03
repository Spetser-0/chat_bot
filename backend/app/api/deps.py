"""
app/api/deps.py
────────────────
FastAPI dependency functions for authentication, authorization,
database sessions, and ownership verification.

These are the ONLY way route handlers should obtain the current student.
Route handlers must never extract student identity from request body/query params.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, AuthorizationError, NotFoundError
from app.db.session import get_db
from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    decode_session_token,
    get_dev_student_identity,
    get_student_by_id,
    is_dev_auth_enabled,
)
from app.services.auth_abstraction import AuthIdentity

if TYPE_CHECKING:
    from app.models.deliverable import Deliverable
    from app.models.request import Request


# ──────────────────────────────────────────────────────────────────────────────
# Current Student (Primary Authentication)
# ──────────────────────────────────────────────────────────────────────────────

async def get_current_student(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_dev_auth: Annotated[str | None, Header(alias="X-Dev-Auth", description="Development auth bypass")] = None,
) -> Student:
    """
    Dependency: Verify session cookie and return the authenticated student.
    
    Supports development mode bypass via X-Dev-Auth header (only when DEV_AUTH_ENABLED=true).
    
    Raises AuthenticationError (401) if cookie is missing or invalid.
    """
    # Check for development mode bypass
    if is_dev_auth_enabled() and x_dev_auth:
        dev_identity = await get_dev_student_identity()
        if dev_identity:
            student = await get_student_by_id(dev_identity.student_id, db)
            return student

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise AuthenticationError()

    data = decode_session_token(token)
    try:
        student_id = uuid.UUID(data["sub"])
    except (KeyError, ValueError):
        raise AuthenticationError()

    return await get_student_by_id(student_id, db)


async def get_current_student_id(
    student: Student = Depends(get_current_student),
) -> uuid.UUID:
    """Dependency: Return only the authenticated student's UUID."""
    return student.id


async def get_active_student(
    student: Student = Depends(get_current_student),
) -> Student:
    """
    Dependency: Like get_current_student but also checks status=active.
    """
    if student.status != "active":
        raise AuthorizationError("الحساب غير نشط.")
    return student


# ──────────────────────────────────────────────────────────────────────────────
# Developer/Admin Authorization
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Ownership Verification Dependencies
# ──────────────────────────────────────────────────────────────────────────────

async def verify_request_ownership(
    request_id: uuid.UUID,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> Request:
    """
    Dependency: Verify that the authenticated student owns the request.
    Returns the Request if owned, raises 403/404 otherwise.
    """
    from app.models.request import Request as RequestModel
    result = await db.execute(
        select(RequestModel).where(RequestModel.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if req is None:
        raise AuthorizationError("المورد المطلوب غير موجود.")
    
    if req.student_id != student.id:
        raise AuthorizationError("ليس لديك إذن للوصول إلى هذا المورد.")
    
    return req


async def verify_deliverable_ownership(
    deliverable_id: uuid.UUID,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> Deliverable:
    """
    Dependency: Verify that the authenticated student owns the deliverable.
    Returns the Deliverable if owned, raises 403/404 otherwise.
    """
    import logging

    from app.models.deliverable import Deliverable as DeliverableModel
    logger = logging.getLogger(__name__)
    logger.info(f"verify_deliverable_ownership: looking for deliverable_id={deliverable_id}, student.id={student.id}")
    result = await db.execute(
        select(DeliverableModel).where(DeliverableModel.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    logger.info(f"verify_deliverable_ownership: deliverable found: {deliverable is not None}")
    if deliverable:
        logger.info(f"  deliverable.student_id={deliverable.student_id}, student.id={student.id}")
    
    if deliverable is None:
        logger.warning(f"Deliverable not found: {deliverable_id}")
        raise NotFoundError("المورد المطلوب غير موجود.")
    
    if deliverable.student_id != student.id:
        logger.warning(f"Ownership mismatch: deliverable.student_id={deliverable.student_id}, student.id={student.id}")
        raise AuthorizationError("ليس لديك إذن للوصول إلى هذا المورد.")
    
    return deliverable


async def verify_credit_balance_ownership(
    student: Student = Depends(get_current_student),
) -> Student:
    """
    Dependency: Verify ownership of credit balance.
    Simply returns the authenticated student (their own balance).
    """
    return student


async def verify_request_history_ownership(
    student: Student = Depends(get_current_student),
) -> Student:
    """
    Dependency: Verify ownership of request history.
    Returns the authenticated student (their own history).
    """
    return student


# ──────────────────────────────────────────────────────────────────────────────
# AuthIdentity Extraction (for services that need the abstraction)
# ──────────────────────────────────────────────────────────────────────────────

def get_auth_identity(student: Student = Depends(get_current_student)) -> AuthIdentity:
    """
    Dependency: Extract AuthIdentity from authenticated student.
    Services should use this instead of raw Student model.
    """
    return AuthIdentity(
        student_id=student.id,
        role=student.role,
        email=student.email,
        display_name=student.display_name,
    )