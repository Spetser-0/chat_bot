"""
tests/integration/test_admin_rbac.py
────────────────────────────────────
Lesson 8.1 — Role-based access control matrix.

Roles: student → 401 (anon) / 403; developer → reads only;
admin → mutations; superadmin → everything incl. dangerous ops.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
)


async def _make_user(db, role: str) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"{role}_{uuid.uuid4().hex[:6]}@t.com",
        display_name=role.title(),
        password_hash=hash_password("pass12345"),
        role=role,
        status="active",
        credit_balance=0,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


def _client(app: FastAPI, student: Student) -> AsyncClient:
    token = create_session_token(student.id, student.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    )


class TestRBACMatrix:
    """GET /admin/referrals exercises the developer/admin/superadmin tiers."""

    @pytest.mark.asyncio
    async def test_anonymous_401(self, client):
        resp = await client.get("/api/v1/admin/referrals")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_student_403(self, app, db):
        student = await _make_user(db, "student")
        async with _client(app, student) as c:
            assert (await c.get("/api/v1/admin/referrals")).status_code == 403

    @pytest.mark.asyncio
    async def test_developer_reads_ok_mutations_403(self, app, db):
        dev = await _make_user(db, "developer")
        async with _client(app, dev) as c:
            assert (await c.get("/api/v1/admin/referrals")).status_code == 200
            resp = await c.post(
                f"/api/v1/admin/referrals/{uuid.uuid4()}/revoke")
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_mutations_allowed(self, app, db):
        admin = await _make_user(db, "admin")
        async with _client(app, admin) as c:
            assert (await c.get("/api/v1/admin/referrals")).status_code == 200
            # Unknown id → 404 (not 403): admin passed the RBAC gate.
            resp = await c.post(
                f"/api/v1/admin/referrals/{uuid.uuid4()}/revoke")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_superadmin_full_access(self, app, db):
        sa = await _make_user(db, "superadmin")
        async with _client(app, sa) as c:
            assert (await c.get("/api/v1/admin/referrals")).status_code == 200
            resp = await c.post(
                f"/api/v1/admin/referrals/{uuid.uuid4()}/revoke")
            assert resp.status_code == 404  # passed RBAC, entity missing

    @pytest.mark.asyncio
    async def test_banned_admin_denied(self, app, db):
        """A banned admin must not use admin endpoints."""
        admin = await _make_user(db, "admin")
        admin.status = "banned"
        await db.commit()
        async with _client(app, admin) as c:
            resp = await c.get("/api/v1/admin/referrals")
            assert resp.status_code == 403
