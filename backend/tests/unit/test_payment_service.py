"""
tests/unit/test_payment_service.py
───────────────────────────────────
Lessons 6.1–6.2 — gateway contract, webhook verification, crediting,
idempotency, underpayment rejection. MockCryptoProvider only — no network.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import NotFoundError, ValidationError
from app.db.session import Base
from app.models.payment_invoice import PaymentInvoice, PaymentStatus
from app.models.student import Student
from app.models.webhook_event import WebhookEvent
from app.services.credit_service import CreditService
from app.services.payment_service import MockCryptoProvider, PaymentService

SECRET = "test-webhook-secret"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def student(db):
    s = Student(id=uuid.uuid4(), email=f"pay{uuid.uuid4().hex[:6]}@t.com",
                role="student", status="active", credit_balance=Decimal("50"),
                is_premium=False)
    db.add(s)
    await db.commit()
    return s


def _svc(db) -> PaymentService:
    return PaymentService(db, MockCryptoProvider())


def _signed(payload: dict) -> tuple[bytes, str]:
    raw = json.dumps(payload).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha512).hexdigest()
    return raw, sig


class TestInvoiceLifecycle:
    @pytest.mark.asyncio
    async def test_create_invoice_is_deterministic(self, db, student):
        svc = _svc(db)
        key = f"inv-{uuid.uuid4()}"
        a = await svc.create_invoice(user_id=student.id, amount_usd=Decimal("10"),
                                     currency="USDT", idempotency_key=key)
        b = await svc.create_invoice(user_id=student.id, amount_usd=Decimal("10"),
                                     currency="USDT", idempotency_key=key)
        assert a.id == b.id and a.status == PaymentStatus.PENDING
        assert a.crypto_address and a.payment_url
        count = (await db.execute(
            select(PaymentInvoice).where(PaymentInvoice.idempotency_key == key)
        )).scalars().all()
        assert len(count) == 1

    @pytest.mark.asyncio
    async def test_create_zero_rejected(self, db, student):
        with pytest.raises(ValidationError):
            await _svc(db).create_invoice(user_id=student.id,
                                          amount_usd=Decimal("0"),
                                          currency="USDT",
                                          idempotency_key=f"z-{uuid.uuid4()}")


class TestWebhookVerification:
    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, db, student):
        inv = await _svc(db).create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"w-{uuid.uuid4()}")
        raw, _ = _signed({"external_id": inv.external_invoice_id, "event": "paid"})
        with pytest.raises(ValidationError):
            await _svc(db).verify_and_record_webhook(
                payload=raw, signature="bad-signature", secret=SECRET)

    @pytest.mark.asyncio
    async def test_malformed_payload_rejected(self, db):
        with pytest.raises(ValidationError):
            await _svc(db).verify_and_record_webhook(
                payload=b"not json",
                signature=hmac.new(SECRET.encode(), b"not json",
                                   hashlib.sha512).hexdigest(),
                secret=SECRET,
            )

    @pytest.mark.asyncio
    async def test_duplicate_external_id_returns_same_event(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"d-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id,
                            "event": "paid"})
        e1 = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                 secret=SECRET)
        e2 = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                 secret=SECRET)
        assert e1.id == e2.id
        rows = (await db.execute(
            select(WebhookEvent).where(WebhookEvent.external_id == inv.external_invoice_id)
        )).scalars().all()
        assert len(rows) == 1


class TestPaidEvent:
    @pytest.mark.asyncio
    async def test_paid_credits_user(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"p-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id, "event": "paid"})
        event = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                    secret=SECRET)
        await svc.handle_event(event)

        fresh = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        assert fresh == Decimal("50") + Decimal("10") * Decimal("100")
        assert inv.status == PaymentStatus.PAID

    @pytest.mark.asyncio
    async def test_paid_replay_credits_once(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"r-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id, "event": "paid"})
        event = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                    secret=SECRET)
        await svc.handle_event(event)
        # replay through both entry points — neither double credits
        event2 = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                     secret=SECRET)
        await svc.handle_event(event2)
        fresh = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        assert fresh == Decimal("50") + Decimal("10") * Decimal("100")

    @pytest.mark.asyncio
    async def test_underpayment_rejected_no_credit(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"u-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id, "event": "paid"})
        event = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                    secret=SECRET)
        with pytest.raises(ValidationError):
            await svc.handle_event(event, paid_amount_usd=Decimal("9.50"))
        fresh = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        assert fresh == Decimal("50")  # unchanged
        assert inv.status == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_overpayment_credited_with_full_amount(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"o-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id, "event": "paid"})
        event = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                    secret=SECRET)
        await svc.handle_event(event, paid_amount_usd=Decimal("12"))
        fresh = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        # generous customer pays 12 but we only promised 10; we credit the
        # full 12 (better than zakat for us, safer than rejecting)
        assert fresh == Decimal("50") + Decimal("12") * Decimal("100")


class TestClosedEvents:
    @pytest.mark.asyncio
    async def test_expired_marks_no_credit(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"e-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id, "event": "expired"})
        event = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                    secret=SECRET)
        await svc.handle_event(event)
        assert inv.status == PaymentStatus.EXPIRED
        fresh = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        assert fresh == Decimal("50")

    @pytest.mark.asyncio
    async def test_unknown_event_type_rejected(self, db, student):
        svc = _svc(db)
        inv = await svc.create_invoice(
            user_id=student.id, amount_usd=Decimal("10"), currency="USDT",
            idempotency_key=f"x-{uuid.uuid4()}")
        raw, sig = _signed({"external_id": inv.external_invoice_id, "event": "stalled"})
        event = await svc.verify_and_record_webhook(payload=raw, signature=sig,
                                                    secret=SECRET)
        with pytest.raises(ValidationError):
            await svc.handle_event(event)
        assert event.error == "ValidationError"  # recorded for triage

    @pytest.mark.asyncio
    async def test_webhook_without_invoice_404(self, db):
        raw, sig = _signed({"external_id": f"ghost-{uuid.uuid4()}", "event": "paid"})
        event = await _svc(db).verify_and_record_webhook(
            payload=raw, signature=sig, secret=SECRET)
        with pytest.raises(NotFoundError):
            await _svc(db).handle_event(event)
