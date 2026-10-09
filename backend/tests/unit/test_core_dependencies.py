"""
tests/unit/test_core_dependencies.py
────────────────────────────────────
Unit tests for Phase 2 role-gate dependencies:
require_admin / require_developer / require_superadmin.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.dependencies import require_admin, require_developer, require_superadmin
from app.core.errors import AuthorizationError
from app.models.student import Student


def _student(role: str, status: str = "active") -> Student:
    return Student(
        id=uuid.uuid4(),
        email=f"{role}@test.com",
        role=role,
        status=status,
    )


class TestRequireAdmin:
    async def test_admin_allowed(self):
        s = _student("admin")
        assert await require_admin(s) is s

    async def test_developer_allowed(self):
        s = _student("developer")
        assert await require_admin(s) is s

    async def test_superadmin_allowed(self):
        s = _student("superadmin")
        assert await require_admin(s) is s

    async def test_normal_student_rejected(self):
        with pytest.raises(AuthorizationError):
            await require_admin(_student("student"))


class TestRequireDeveloper:
    async def test_developer_allowed(self):
        s = _student("developer")
        assert await require_developer(s) is s

    async def test_superadmin_allowed(self):
        s = _student("superadmin")
        assert await require_developer(s) is s

    async def test_admin_rejected(self):
        with pytest.raises(AuthorizationError):
            await require_developer(_student("admin"))

    async def test_normal_student_rejected(self):
        with pytest.raises(AuthorizationError):
            await require_developer(_student("student"))


class TestRequireSuperadmin:
    async def test_superadmin_allowed(self):
        s = _student("superadmin")
        assert await require_superadmin(s) is s

    async def test_admin_rejected(self):
        with pytest.raises(AuthorizationError):
            await require_superadmin(_student("admin"))

    async def test_developer_rejected(self):
        with pytest.raises(AuthorizationError):
            await require_superadmin(_student("developer"))

    async def test_normal_student_rejected(self):
        with pytest.raises(AuthorizationError):
            await require_superadmin(_student("student"))
