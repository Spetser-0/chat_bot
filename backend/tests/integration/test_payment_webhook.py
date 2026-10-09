"""
tests/integration/test_payment_webhook.py
──────────────────────────────────────────
Lesson 6.5 — webhook ingress: signature verify, dedupe, credit-once.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.payment_invoice import PaymentStatus
from app.models.student import Student


def _signed(body: dict, secret: str) -> tuple[bytes, str]:
    raw = json.dumps(body).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    return raw, sig


class TestWebhookEndpoint:
    async def _make_invoice(self, authenticated_client) -> tuple[str, str]:
        r = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": f"wh-{uuid.uuid4()}"})
        assert r.status_code == 201
        body = r.json()
        return body["invoice_id"], body["crypto_address"]  # ext id = mock-… via address lookup

    @pytest.mark.asyncio
    async def test_invalid_signature_400(self, client):
        raw = json.dumps({"external_id": "anything", "event": "paid"}).encode()
        resp = await client.post("/api/v1/payments/webhook", content=raw,
                                 headers={"x-signature": "bogus",
                                          "content-type": "application/json"})
        assert resp.status_code == 400
        assert "توقيع" in resp.text

    @pytest.mark.asyncio
    async def test_missing_signature_400(self, client):
        resp = await client.post("/api/v1/payments/webhook",
                                 content=b"{}", headers={"content-type": "application/json"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_paid_event_credits_once(self, client, authenticated_client, db, student):
        # NOTE: `db` session is shared (StaticPool) — capture the starting
        # balance BEFORE the webhook mutates it in-place.
        starting = student.credit_balance

        # create invoice via API so it's genuinely pending in the DB
        r = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": f"web-{uuid.uuid4()}"})
        assert r.status_code == 201

        # find the external invoice id
        from app.models.payment_invoice import PaymentInvoice
        inv = (await db.execute(select(PaymentInvoice)
                               .where(PaymentInvoice.user_id == student.id,
                                      PaymentInvoice.status == PaymentStatus.PENDING)
                               .order_by(PaymentInvoice.created_at.desc())
                               .limit(1))).scalar_one()

        raw, sig = _signed({"external_id": inv.external_invoice_id,
                            "event": "paid"}, "dev-webhook-secret")

        # first delivery
        resp = await client.post("/api/v1/payments/webhook", content=raw,
                                 headers={"x-signature": sig,
                                          "content-type": "application/json"})
        assert resp.status_code == 200
        assert resp.json()["invoice_status"] == "paid"

        # replay — must not double-credit
        resp2 = await client.post("/api/v1/payments/webhook", content=raw,
                                  headers={"x-signature": sig,
                                           "content-type": "application/json"})
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True

        # balance reflects exactly one topup of 10 USD → 1000 credits
        after = (await db.execute(select(Student.credit_balance)
                                  .where(Student.id == student.id))).scalar_one()
        assert after == starting + Decimal("1000")

    @pytest.mark.asyncio
    async def test_unknown_invoice_404_safe(self, client, db):
        ext = f"ghost-{uuid.uuid4()}"
        raw, sig = _signed({"external_id": ext, "event": "paid"},
                           "dev-webhook-secret")
        resp = await client.post("/api/v1/payments/webhook", content=raw,
                                 headers={"x-signature": sig,
                                          "content-type": "application/json"})
        assert resp.status_code == 404  # verified signature but no invoice

    @pytest.mark.asyncio
    async def test_expired_event_marks_no_credit(self, client, authenticated_client, db, student):
        r = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "idempotency_key": f"exp-{uuid.uuid4()}"})
        from app.models.payment_invoice import PaymentInvoice
        inv = (await db.execute(select(PaymentInvoice)
                               .where(PaymentInvoice.user_id == student.id,
                                      PaymentInvoice.status == PaymentStatus.PENDING)
                               .order_by(PaymentInvoice.created_at.desc())
                               .limit(1))).scalar_one()

        raw, sig = _signed({"external_id": inv.external_invoice_id,
                            "event": "expired"}, "dev-webhook-secret")
        resp = await client.post("/api/v1/payments/webhook", content=raw,
                                 headers={"x-signature": sig,
                                          "content-type": "application/json"})
        assert resp.status_code == 200
        assert resp.json()["invoice_status"] == "expired"
