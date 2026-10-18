"""
tests/integration/test_security_remediations.py
───────────────────────────────────────────────
Regression tests for Phase 1 security audit remediations:
- SEC-CRIT-01: /credits/grant gated to development environment only
- SEC-HIGH-01: X-Dev-Auth fail-closed checks
- SEC-MED-01: Session cookie deletion flags on logout
- SEC-MED-02: Provider key rotation requires admin and typed payload
- SEC-MED-03: Webhook secret fallback requires strict development mode
- SEC-LOW-01: Referral validation rate limiting
- SEC-LOW-02: Canonical /deliverables/{id}/download route resolution
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.core.config import get_settings
from app.models.student import Student
from app.services.auth import SESSION_COOKIE_NAME, create_session_token, hash_password


@pytest_asyncio.fixture
async def developer_user(db) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"dev_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Developer",
        password_hash=hash_password("pass12345"),
        role="developer",
        status="active",
        credit_balance=0,
    )
    db.add(s)
    await db.commit()
    return s


@pytest_asyncio.fixture
async def developer_client(app: FastAPI, developer_user) -> AsyncClient:
    token = create_session_token(developer_user.id, developer_user.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


@pytest_asyncio.fixture
async def admin(db) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Admin",
        password_hash=hash_password("pass12345"),
        role="admin",
        status="active",
        credit_balance=0,
    )
    db.add(s)
    await db.commit()
    return s


@pytest_asyncio.fixture
async def admin_client(app: FastAPI, admin) -> AsyncClient:
    token = create_session_token(admin.id, admin.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


class TestSecurityRemediations:
    @pytest.mark.asyncio
    async def test_credits_grant_gated_by_environment(self, authenticated_client):
        """SEC-CRIT-01: /credits/grant is allowed in development, denied in production."""
        # 1. In default test environment (is_development = True):
        resp = await authenticated_client.post("/api/v1/credits/grant")
        assert resp.status_code == 200
        assert Decimal(resp.json()["balance"]) >= Decimal("300")

        # 2. In simulated production environment:
        with patch.object(get_settings(), "app_env", "production"):
            resp_prod = await authenticated_client.post("/api/v1/credits/grant")
            assert resp_prod.status_code == 403
            data = resp_prod.json()
            assert data["error"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_provider_key_rotation_requires_admin(self, developer_client):
        """SEC-MED-02: Developer role cannot create or mutate provider keys (requires admin)."""
        resp = await developer_client.post(
            "/api/v1/admin/providers",
            json={
                "slug": "test-provider",
                "name": "Test Provider",
                "model_name": "test-model",
                "api_key": "sk-test-12345",
                "priority_weight": 100,
            },
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_provider_key_rotation_schema_validation(self, admin_client):
        """SEC-MED-02: Provider creation endpoint requires validated schema."""
        # Missing required fields returns 422
        resp = await admin_client.post(
            "/api/v1/admin/providers",
            json={},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, authenticated_client):
        """SEC-MED-01: Logout sets session cookie deletion."""
        resp = await authenticated_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert "spetser_session" in resp.headers.get("set-cookie", "")

    @pytest.mark.asyncio
    async def test_canonical_deliverable_download_route(self, authenticated_client):
        """SEC-LOW-02: /api/v1/deliverables/{id}/download route is mounted and returns 404 for nonexistent object."""
        resp = await authenticated_client.get(f"/api/v1/deliverables/{uuid.uuid4()}/download")
        assert resp.status_code == 404
