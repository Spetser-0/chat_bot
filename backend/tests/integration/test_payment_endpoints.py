"""
tests/integration/test_payment_endpoints.py
────────────────────────────────────────────
Lesson 6.3 — POST /payments/create-invoice + GET /payments/{id}/status.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.models.student import Student
from app.services.auth import SESSION_COOKIE_NAME, create_session_token, hash_password


@pytest_asyncio.fixture
async def other_client(app: FastAPI, db) -> AsyncClient:
    """A second student, to prove ownership isolation."""
    other = Student(id=uuid.uuid4(), email=f"o{uuid.uuid4().hex[:6]}@t.com",
                    role="student", status="active",
                    password_hash=hash_password("pass12345"),
                    credit_balance=0, is_premium=False)
    db.add(other)
    await db.commit()
    token = create_session_token(other.id, other.role)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


class TestCreateInvoice:
    @pytest.mark.asyncio
    async def test_create_and_idempotent_replay(self, authenticated_client):
        key = f"ui-{uuid.uuid4()}"
        payload = {"amount_usd": "25", "currency": "USDT",
                   "idempotency_key": key}
        r1 = await authenticated_client.post(
            "/api/v1/payments/create-invoice", json=payload)
        assert r1.status_code == 201, r1.text
        body = r1.json()
        assert body["status"] == "pending"
        assert body["credits_if_paid"] == "2500"  # 25 × 100
        assert body["crypto_address"].startswith("mock-address-")

        r2 = await authenticated_client.post(
            "/api/v1/payments/create-invoice", json=payload)
        assert r2.status_code == 201
        assert r2.json()["invoice_id"] == body["invoice_id"]  # same invoice

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client):
        resp = await client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": f"x-{uuid.uuid4()}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_amount_validation(self, authenticated_client):
        resp = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "-5", "idempotency_key": f"y-{uuid.uuid4()}"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_short_idempotency_key_rejected(self, authenticated_client):
        resp = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": "short"})
        assert resp.status_code == 422


class TestStatus:
    @pytest.mark.asyncio
    async def test_owner_can_read_status(self, authenticated_client):
        r = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": f"s-{uuid.uuid4()}"})
        inv_id = r.json()["invoice_id"]

        resp = await authenticated_client.get(f"/api/v1/payments/{inv_id}/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert body["paid_at"] is None

    @pytest.mark.asyncio
    async def test_non_owner_forbidden(self, authenticated_client, db, other_client):
        r = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": f"t-{uuid.uuid4()}"})
        inv_id = r.json()["invoice_id"]

        resp = await other_client.get(f"/api/v1/payments/{inv_id}/status")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_invoice_404(self, authenticated_client):
        resp = await authenticated_client.get(f"/api/v1/payments/{uuid.uuid4()}/status")
        assert resp.status_code == 404
