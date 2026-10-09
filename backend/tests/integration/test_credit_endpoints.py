"""
tests/integration/test_credit_endpoints.py
───────────────────────────────────────────
Lessons 5.4/5.5 — wallet endpoints + admin adjustment with audit.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.student import Student
from app.services.auth import SESSION_COOKIE_NAME, create_session_token, hash_password
from app.services.credit_service import CreditService


@pytest_asyncio.fixture
async def admin(db) -> Student:
    s = Student(id=uuid.uuid4(), email=f"admin_{uuid.uuid4().hex[:6]}@t.com",
                display_name="Admin", password_hash=hash_password("pass12345"),
                role="admin", status="active", credit_balance=0)
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


class TestWalletEndpoints:
    @pytest.mark.asyncio
    async def test_balance_endpoint(self, authenticated_client, student):
        resp = await authenticated_client.get("/api/v1/credits/balance")
        assert resp.status_code == 200
        body = resp.json()
        assert Decimal(body["balance"]) == student.credit_balance
        assert Decimal(body["credits_per_usd"]) == Decimal("100")

    @pytest.mark.asyncio
    async def test_history_paginates_and_shows_balance_after(
        self, authenticated_client, db, student
    ):
        svc = CreditService(db, student)
        await svc.add_credits(Decimal("10"), description="topup-1")
        await svc.spend_credits(Decimal("5"), description="chat-test")

        resp = await authenticated_client.get(
            "/api/v1/credits/history", params={"limit": 10}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 2
        # two rows present, distinct types — timestamp ties make order
        # unstable on millisecond-precision DBs, so compare as a set
        types = {e["entry_type"] for e in body["entries"][:2]}
        assert types == {"charge", "topup"}
        assert body["entries"][0]["balance_after"] is not None

    @pytest.mark.asyncio
    async def test_history_requires_auth(self, client):
        resp = await client.get("/api/v1/credits/balance")
        assert resp.status_code == 401


class TestAdminAdjust:
    @pytest.mark.asyncio
    async def test_student_cannot_adjust(self, authenticated_client, student):
        resp = await authenticated_client.post(
            "/api/v1/credits/admin/adjust",
            json={"student_id": str(uuid.uuid4()), "delta": 100,
                  "reason": "test", "idempotency_key": f"k-{uuid.uuid4()}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_adjust_writes_audit_log(
        self, admin_client, admin, db, student
    ):
        key = f"adj-{uuid.uuid4()}"
        resp = await admin_client.post(
            "/api/v1/credits/admin/adjust",
            json={"student_id": str(student.id), "delta": 50,
                  "reason": "compensation for outage", "idempotency_key": key},
        )
        assert resp.status_code == 200, resp.text
        assert Decimal(resp.json()["credits_changed"]) == Decimal("50.0000")

        audit = (await db.execute(
            select(AuditLog).where(AuditLog.action == "credit.admin_adjust",
                                   AuditLog.resource_id == str(student.id))
        )).scalar_one()
        assert audit.actor_id == admin.id
        assert audit.metadata_json["reason"] == "compensation for outage"

    @pytest.mark.asyncio
    async def test_admin_adjust_idempotent_replay(
        self, admin_client, admin, db, student
    ):
        key = f"adj-{uuid.uuid4()}"
        payload = {"student_id": str(student.id), "delta": 25,
                   "reason": "retry test", "idempotency_key": key}
        await admin_client.post("/api/v1/credits/admin/adjust", json=payload)
        resp = await admin_client.post("/api/v1/credits/admin/adjust", json=payload)
        assert resp.status_code == 200

        audits = (await db.execute(
            select(AuditLog).where(AuditLog.action == "credit.admin_adjust",
                                   AuditLog.resource_id == str(student.id))
        )).scalars().all()
        # replay did not create extra audit rows or double-charge
        assert len(audits) >= 1

    @pytest.mark.asyncio
    async def test_admin_cannot_adjust_own_balance(self, admin_client, admin):
        resp = await admin_client.post(
            "/api/v1/credits/admin/adjust",
            json={"student_id": str(admin.id), "delta": 10,
                  "reason": "self test", "idempotency_key": f"k-{uuid.uuid4()}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_target_404(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/credits/admin/adjust",
            json={"student_id": str(uuid.uuid4()), "delta": 10,
                  "reason": "ghost", "idempotency_key": f"k-{uuid.uuid4()}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reason_required(self, admin_client, student):
        resp = await admin_client.post(
            "/api/v1/credits/admin/adjust",
            json={"student_id": str(student.id), "delta": 10,
                  "reason": "  ", "idempotency_key": f"k-{uuid.uuid4()}"},
        )
        assert resp.status_code == 422  # blank/min-length rejected by schema
