"""
tests/integration/test_admin_providers.py
─────────────────────────────────────────
Lesson 8.2 — Admin AI provider management endpoints.

Security assertions:
- API key NEVER appears in any response body (only masked preview).
- Reads: developer+; mutations: admin+.
- Every mutation writes an audit_logs row.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.audit_log import AuditLog
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


def _client(app: FastAPI, user: Student) -> AsyncClient:
    token = create_session_token(user.id, user.role)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    )


PROVIDER_PAYLOAD = {
    "name": "OpenAI Test",
    "slug": f"openai-test-{uuid.uuid4().hex[:6]}",
    "model_name": "gpt-4o-mini",
    "api_key": "sk-test-1234567890abcdef",
}


class TestProviderRBAC:
    @pytest.mark.asyncio
    async def test_anonymous_401(self, client):
        assert (await client.get("/api/v1/admin/providers")).status_code == 401

    @pytest.mark.asyncio
    async def test_student_403(self, app, db):
        u = await _make_user(db, "student")
        async with _client(app, u) as c:
            assert (await c.get("/api/v1/admin/providers")).status_code == 403

    @pytest.mark.asyncio
    async def test_developer_reads_cannot_mutate(self, app, db):
        dev = await _make_user(db, "developer")
        async with _client(app, dev) as c:
            assert (await c.get("/api/v1/admin/providers")).status_code == 200
            resp = await c.post("/api/v1/admin/providers",
                                json={**PROVIDER_PAYLOAD,
                                      "slug": f"x-{uuid.uuid4().hex[:6]}"})
            assert resp.status_code == 403


class TestProviderCrud:
    @pytest.mark.asyncio
    async def test_admin_create_returns_masked_key(self, app, db):
        admin = await _make_user(db, "admin")
        async with _client(app, admin) as c:
            resp = await c.post("/api/v1/admin/providers",
                                json=PROVIDER_PAYLOAD)
            assert resp.status_code == 201
            body = resp.json()
            assert body["slug"] == PROVIDER_PAYLOAD["slug"]
            # Masked preview — never the plaintext key.
            assert "sk-test-1234567890abcdef" not in resp.text
            assert "***" in body["api_key_masked"]

    @pytest.mark.asyncio
    async def test_duplicate_slug_409(self, app, db):
        admin = await _make_user(db, "admin")
        async with _client(app, admin) as c:
            payload = {**PROVIDER_PAYLOAD,
                       "slug": f"dup-{uuid.uuid4().hex[:6]}"}
            assert (await c.post("/api/v1/admin/providers",
                                 json=payload)).status_code == 201
            assert (await c.post("/api/v1/admin/providers",
                                 json=payload)).status_code == 409

    @pytest.mark.asyncio
    async def test_list_and_get_never_leak_key(self, app, db):
        admin = await _make_user(db, "admin")
        slug = f"leak-{uuid.uuid4().hex[:6]}"
        async with _client(app, admin) as c:
            await c.post("/api/v1/admin/providers",
                         json={**PROVIDER_PAYLOAD, "slug": slug})
            listing = await c.get("/api/v1/admin/providers")
            single = await c.get(f"/api/v1/admin/providers/{slug}")
            assert listing.status_code == 200
            assert single.status_code == 200
            assert PROVIDER_PAYLOAD["api_key"] not in listing.text
            assert PROVIDER_PAYLOAD["api_key"] not in single.text

    @pytest.mark.asyncio
    async def test_update_and_toggle(self, app, db):
        admin = await _make_user(db, "admin")
        slug = f"upd-{uuid.uuid4().hex[:6]}"
        async with _client(app, admin) as c:
            await c.post("/api/v1/admin/providers",
                         json={**PROVIDER_PAYLOAD, "slug": slug})
            resp = await c.patch(f"/api/v1/admin/providers/{slug}",
                                 json={"priority_weight": 250})
            assert resp.status_code == 200
            assert resp.json()["priority_weight"] == 250
            assert PROVIDER_PAYLOAD["api_key"] not in resp.text

            resp = await c.post(f"/api/v1/admin/providers/{slug}/toggle-active")
            assert resp.status_code == 200
            assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete(self, app, db):
        admin = await _make_user(db, "admin")
        slug = f"del-{uuid.uuid4().hex[:6]}"
        async with _client(app, admin) as c:
            await c.post("/api/v1/admin/providers",
                         json={**PROVIDER_PAYLOAD, "slug": slug})
            assert (await c.delete(
                f"/api/v1/admin/providers/{slug}")).status_code == 204
            assert (await c.get(
                f"/api/v1/admin/providers/{slug}")).status_code == 404

    @pytest.mark.asyncio
    async def test_test_endpoint_healthy(self, app, db):
        admin = await _make_user(db, "admin")
        slug = f"tst-{uuid.uuid4().hex[:6]}"
        async with _client(app, admin) as c:
            await c.post("/api/v1/admin/providers",
                         json={**PROVIDER_PAYLOAD, "slug": slug})
            resp = await c.post(f"/api/v1/admin/providers/{slug}/test")
            assert resp.status_code == 200
            assert resp.json()["healthy"] is True


class TestProviderAudit:
    @pytest.mark.asyncio
    async def test_mutations_write_audit_rows(self, app, db):
        admin = await _make_user(db, "admin")
        slug = f"aud-{uuid.uuid4().hex[:6]}"
        async with _client(app, admin) as c:
            r = await c.post("/api/v1/admin/providers",
                             json={**PROVIDER_PAYLOAD, "slug": slug})
            assert r.status_code == 201
            provider_id = r.json()["id"]
            await c.patch(f"/api/v1/admin/providers/{slug}",
                          json={"priority_weight": 50})
            await c.post(f"/api/v1/admin/providers/{slug}/toggle-active")

        actions = [
            row.action for row in (await db.execute(
                select(AuditLog).where(
                    AuditLog.resource_type == "ai_provider",
                    AuditLog.resource_id == provider_id,
                )
            )).scalars().all()
        ]
        assert "provider.created" in actions
        assert "provider.updated" in actions
        assert "provider.toggled" in actions
