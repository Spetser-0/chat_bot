"""
tests/integration/test_admin_skills.py
───────────────────────────────────────
Admin skill CRUD endpoints (Lesson 4.6).

RBAC matrix:
- anonymous → 401
- student    → 403 on mutations AND reads
- developer  → 200 reads, 403 mutations
- admin      → full CRUD
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.models.student import Student
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
)

def payload(**over):
    """Slug is unique per call — the suite shares one session-level DB."""
    unique = uuid.uuid4().hex[:8]
    base = {
        "name": "مدرس الرياضيات",
        "slug": f"math-tutor-{unique}",
        "system_prompt": "أنت معلم رياضيات. الطالب {{user_name}}.",
        "temperature": 0.5,
        "max_tokens": 2048,
        "is_public": True,
        "is_premium": False,
        "tools": [{"tool_name": "calculator", "tool_config": {"precision": 2}}],
    }
    base.update(over)
    return base


@pytest_asyncio.fixture
async def admin(db) -> Student:
    s = Student(
        id=uuid.uuid4(), email=f"admin_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Admin", password_hash=hash_password("pass12345"),
        role="admin", status="active", credit_balance=0,
    )
    db.add(s)
    await db.commit()
    return s


@pytest_asyncio.fixture
async def admin_client(app: FastAPI, admin) -> AsyncClient:
    token = create_session_token(admin.id, admin.role)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def developer_client(app: FastAPI, developer) -> AsyncClient:
    token = create_session_token(developer.id, developer.role)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


class TestRBAC:
    @pytest.mark.asyncio
    async def test_anonymous_rejected(self, client):
        resp = await client.get("/api/v1/admin/skills")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_student_forbidden(self, authenticated_client):
        for resp in [
            await authenticated_client.get("/api/v1/admin/skills"),
            await authenticated_client.post("/api/v1/admin/skills", json=payload()),
        ]:
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_developer_can_read_not_write(self, developer_client):
        assert (await developer_client.get("/api/v1/admin/skills")).status_code == 200
        resp = await developer_client.post("/api/v1/admin/skills", json=payload())
        assert resp.status_code == 403


class TestSkillCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get(self, admin_client):
        resp = await admin_client.post("/api/v1/admin/skills", json=payload())
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["slug"].startswith("math-tutor-")
        assert body["version"] == 1
        assert body["tools"][0]["tool_name"] == "calculator"

        got = await admin_client.get(f"/api/v1/admin/skills/{body['id']}")
        assert got.status_code == 200

    @pytest.mark.asyncio
    async def test_duplicate_slug_conflict(self, admin_client):
        same = payload()
        await admin_client.post("/api/v1/admin/skills", json=same)
        resp = await admin_client.post("/api/v1/admin/skills", json=same)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_unknown_variable_rejected_422(self, admin_client):
        bad = dict(payload(), system_prompt="مرحباً {{unknown_var}}")
        resp = await admin_client.post("/api/v1/admin/skills", json=bad)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_tool_rejected_422(self, admin_client):
        bad = dict(payload(), tools=[{"tool_name": "shell", "tool_config": None}])
        resp = await admin_client.post("/api/v1/admin/skills", json=bad)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_bumps_version(self, admin_client):
        create = await admin_client.post("/api/v1/admin/skills", json=payload())
        sid = create.json()["id"]
        resp = await admin_client.patch(
            f"/api/v1/admin/skills/{sid}", json={"temperature": 1.1}
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 2
        assert float(resp.json()["temperature"]) == 1.1

    @pytest.mark.asyncio
    async def test_patch_tools_replaces_old(self, admin_client):
        create = await admin_client.post("/api/v1/admin/skills", json=payload())
        sid = create.json()["id"]
        resp = await admin_client.patch(
            f"/api/v1/admin/skills/{sid}",
            json={"tools": [{"tool_name": "web_search",
                             "tool_config": {"max_results": 3}}]},
        )
        names = [t["tool_name"] for t in resp.json()["tools"]]
        assert names == ["web_search"]

    @pytest.mark.asyncio
    async def test_delete(self, admin_client):
        create = await admin_client.post("/api/v1/admin/skills", json=payload())
        sid = create.json()["id"]
        assert (await admin_client.delete(f"/api/v1/admin/skills/{sid}")).status_code == 204
        assert (await admin_client.get(f"/api/v1/admin/skills/{sid}")).status_code == 404

    @pytest.mark.asyncio
    async def test_get_missing_404(self, admin_client):
        resp = await admin_client.get(f"/api/v1/admin/skills/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_test_endpoint_safe_mock(self, admin_client):
        create = await admin_client.post("/api/v1/admin/skills", json=payload())
        sid = create.json()["id"]
        resp = await admin_client.post(
            f"/api/v1/admin/skills/{sid}/test", json={"sample_message": "كيف الجمع؟"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["rendered_system_prompt"].startswith("أنت معلم رياضيات")
        # Admin display_name injected into {{user_name}}
        assert "Admin" in body["rendered_system_prompt"]

    @pytest.mark.asyncio
    async def test_meta_count_route_order(self, admin_client):
        resp = await admin_client.get("/api/v1/admin/skills/_meta/count")
        assert resp.status_code == 200
        assert set(resp.json().keys()) == {"total", "public"}
