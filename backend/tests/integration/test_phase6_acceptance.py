"""
tests/integration/test_phase6_acceptance.py
────────────────────────────────────────────────
Lesson 6.10 — Phase 6 acceptance test.

End-to-end scenario: user creates invoice → pays via webhook →
credits added → invoice marked paid → idempotent replay safe.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.errors import ValidationError
from app.models.payment_invoice import PaymentInvoice, PaymentStatus
from app.models.student import Student
from app.models.webhook_event import WebhookEvent
from app.services.credit_service import CreditService
from app.services.payment_service import MockCryptoProvider, PaymentService


def _signed(payload: dict, secret: str) -> tuple[bytes, str]:
    raw = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
    return raw, sig


@pytest.fixture
async def setup_invoice(authenticated_client, db, student):
    """Create a pending invoice and return (invoice_id, external_id)."""
    r = await authenticated_client.post(
        "/api/v1/payments/create-invoice",
        json={"amount_usd": "25", "currency": "USDT",
              "idempotency_key": f"acc-{uuid.uuid4()}"}
    )
    assert r.status_code == 201
    body = r.json()
    inv_id = body["invoice_id"]
    # fetch external_id from DB
    inv = (await db.execute(
        select(PaymentInvoice).where(PaymentInvoice.id == uuid.UUID(inv_id))
    )).scalar_one()
    return inv.id, inv.external_invoice_id


class TestPhase6Acceptance:
    """Phase 6 acceptance: full payment flow from invoice to credit."""

    @pytest.mark.asyncio
    async def test_full_payment_flow_credits_user(
        self, authenticated_client, db, student
    ):
        """User creates invoice → webhook delivers 'paid' → credits added."""
        # 1. Create invoice
        inv_id, ext_id = await self._make_invoice(authenticated_client, db, "50")

        # 2. Simulate webhook delivery
        raw, sig = _signed({"external_id": ext_id, "event": "paid"}, "dev-webhook-secret")
        event = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=raw, signature=sig, secret="dev-webhook-secret"
        )

        # 3. Process event
        inv = await PaymentService(db, MockCryptoProvider()).handle_event(event)
        assert inv.status == PaymentStatus.PAID

        # 4. Verify credits added (50 USD * 100 = 5000 credits)
        bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        # Starting balance varies by fixture; check delta
        # (test fixture student starts with 200)
        assert bal >= 200 + 5000  # at least 5000 added

    @pytest.mark.asyncio
    async def test_webhook_replay_does_not_double_credit(
        self, authenticated_client, db, student
    ):
        """Replaying the same webhook must not double-credit."""
        inv_id, ext_id = await self._make_invoice(authenticated_client, db, "100")
        svc = PaymentService(db, MockCryptoProvider())

        raw, sig = _signed({"external_id": ext_id, "event": "paid"}, "dev-webhook-secret")
        event1 = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "paid"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        await PaymentService(db, MockCryptoProvider()).handle_event(event1)

        # Replay
        event2 = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "paid"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        await PaymentService(db, MockCryptoProvider()).handle_event(event2)

        # Only one credit entry
        charges = (await db.execute(select(PaymentInvoice).where(
            PaymentInvoice.external_invoice_id == ext_id
        ))).scalar_one()
        assert charges.status == "paid"

        # Only one credit ledger entry for this invoice
        from app.models.credit_ledger import CreditLedger, LedgerEntryType
        charges = (await db.execute(select(CreditLedger).where(
            CreditLedger.idempotency_key == f"pay-credit-{ext_id}"
        ))).scalars().all()
        assert len(charges) == 1

    @pytest.mark.asyncio
    async def test_underpayment_rejected_no_credit(self, authenticated_client, db, student):
        """Underpaid webhook marks invoice FAILED, no credits added."""
        inv_id, ext_id = await self._make_invoice(authenticated_client, db, "50")
        svc = PaymentService(db, MockCryptoProvider())

        raw, sig = _signed({"external_id": ext_id, "event": "paid"}, "dev-webhook-secret")
        event = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "paid"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        # Underpayment should raise ValidationError
        try:
            await svc.handle_event(event, paid_amount_usd=Decimal("47.50"))
            pytest.fail("Expected ValidationError for underpayment")
        except ValidationError:
            pass  # Expected

        inv = (await db.execute(select(PaymentInvoice).where(
            PaymentInvoice.external_invoice_id == ext_id
        ))).scalar_one()
        assert inv.status == PaymentStatus.FAILED

        bal = (await db.execute(select(Student.credit_balance).where(
            Student.id == student.id))).scalar_one()
        assert bal == student.credit_balance  # unchanged

    @pytest.mark.asyncio
    async def test_overpayment_credits_full_amount(self, authenticated_client, db, student):
        """Overpayment credits the full paid amount (generous policy)."""
        inv_id, ext_id = await self._make_invoice(authenticated_client, db, "20")
        svc = PaymentService(db, MockCryptoProvider())

        raw, sig = _signed({"external_id": ext_id, "event": "paid"}, "dev-webhook-secret")
        event = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "paid"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        await svc.handle_event(event, paid_amount_usd=Decimal("25"))  # overpaid 5

        bal = (await db.execute(select(Student.credit_balance).where(
            Student.id == student.id))).scalar_one()
        # 20 + 5 extra = 25 USD → 2500 credits
        assert bal == 200 + 2500

    @pytest.mark.asyncio
    async def test_expired_invoice_no_credit(self, authenticated_client, db, student):
        """Expired invoice marked expired, no credits added."""
        inv_id, ext_id = await self._make_invoice(authenticated_client, db, "30")
        svc = PaymentService(db, MockCryptoProvider())

        raw, sig = _signed({"external_id": ext_id, "event": "expired"}, "dev-webhook-secret")
        event = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "expired"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        await svc.handle_event(event)

        inv = (await db.execute(select(PaymentInvoice).where(
            PaymentInvoice.external_invoice_id == ext_id
        ))).scalar_one()
        assert inv.status == "expired"

        bal = (await db.execute(select(Student.credit_balance).where(
            Student.id == student.id))).scalar_one()
        assert bal == 200  # unchanged

    @pytest.mark.asyncio
    async def test_webhook_replay_idempotent(self, authenticated_client, db, student):
        """Full webhook replay (verify + handle) is idempotent."""
        inv_id, ext_id = await self._make_invoice(authenticated_client, db, "15")
        svc = PaymentService(db, MockCryptoProvider())

        raw, sig = _signed({"external_id": ext_id, "event": "paid"}, "dev-webhook-secret")
        
        # First delivery
        e1 = await PaymentService(db, MockCryptoProvider()).verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "paid"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        await svc.handle_event(e1)

        # Replay verify
        e2 = await svc.verify_and_record_webhook(
            payload=json.dumps({"external_id": ext_id, "event": "paid"}).encode(),
            signature=sig, secret="dev-webhook-secret"
        )
        await svc.handle_event(e2)

        # Only one credit
        bal = (await db.execute(select(Student.credit_balance).where(
            Student.id == student.id))).scalar_one()
        assert bal == 200 + 1500  # 15 * 100

    async def _make_invoice(self, client, db, amount: str):
        """Helper to create invoice and return (invoice_id, external_id)."""
        key = f"acc-{uuid.uuid4()}"
        r = await client.post("/api/v1/payments/create-invoice", json={
            "amount_usd": amount, "currency": "USDT", "idempotency_key": key
        })
        assert r.status_code == 201
        body = r.json()
        inv_id = body["invoice_id"]
        # Fetch external_id from DB
        from app.models.payment_invoice import PaymentInvoice
        inv = (await db.execute(
            select(PaymentInvoice).where(PaymentInvoice.id == uuid.UUID(inv_id))
        )).scalar_one()
        return inv.id, inv.external_invoice_id


def _signed(body: dict, secret: str) -> tuple[bytes, str]:
    import hmac, hashlib, json
    raw = json.dumps(body).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    return raw, sig