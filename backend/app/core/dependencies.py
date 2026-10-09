"""
app/core/dependencies.py
────────────────────────
Shared FastAPI dependency helpers for Phase 2+ modules.

Re-exports the canonical auth/session dependencies from app.api.deps and
adds strict role gates:

- get_current_user   alias of get_current_student
- require_admin      admin | developer | superadmin
- require_developer  developer | superadmin
- require_superadmin superadmin only

All role gates build on get_active_student, so accounts that are not in
"active" status (banned/suspended) are rejected before the role check.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import (
    get_active_student,
    get_admin,
    get_auth_identity,
    get_current_student,
    get_current_student_id,
    get_developer,
)
from app.core.errors import AuthorizationError
from app.db.session import get_db
from app.models.student import Student

# Canonical alias used by Phase 2+ modules
get_current_user = get_current_student

_ADMIN_ROLES = frozenset({"admin", "developer", "superadmin"})
_DEVELOPER_ROLES = frozenset({"developer", "superadmin"})
_SUPERADMIN_ROLE = "superadmin"


async def require_admin(
    student: Annotated[Student, Depends(get_active_student)],
) -> Student:
    """Admin-level access: admin, developer, or superadmin role."""
    if student.role not in _ADMIN_ROLES:
        raise AuthorizationError("هذه العملية تتطلب صلاحيات إدارية.")
    return student


async def require_developer(
    student: Annotated[Student, Depends(get_active_student)],
) -> Student:
    """Developer-level access: developer or superadmin role."""
    if student.role not in _DEVELOPER_ROLES:
        raise AuthorizationError("هذه العملية تتطلب صلاحيات مطوّر.")
    return student


async def require_superadmin(
    student: Annotated[Student, Depends(get_active_student)],
) -> Student:
    """Superadmin-only access."""
    if student.role != _SUPERADMIN_ROLE:
        raise AuthorizationError("هذه العملية تتطلب صلاحيات سوبر أدمن.")
    return student


__all__ = [
    "get_db",
    "get_current_user",
    "get_current_student",
    "get_current_student_id",
    "get_active_student",
    "get_admin",
    "get_developer",
    "get_auth_identity",
    "require_admin",
    "require_developer",
    "require_superadmin",
]
