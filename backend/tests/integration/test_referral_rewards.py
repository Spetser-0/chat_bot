"""
tests/integration/test_referral_rewards.py
─────────────────────────────────────────
Lesson 7.5 — Referral reward logic.

Rules verified:
- Reward not granted before payment.
- Payment by a referred user qualifies the referral and schedules a
  PENDING reward (holding period, default 7 days).
- Reward released only after the holding period: referrer gets credits,
  referral flips to REWARDED.
- Release is idempotent (no double credit).
- Duplicate webhook does not duplicate the reward.
- Revoked referral does not pay.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.credit_ledger import CreditLedger
from app.models.payment_invoice import PaymentInvoice
from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardStatus, RewardTransaction
from app.models.student import Student
from app.services.auth import hash_password
from app.services.payment_service import MockCryptoProvider, PaymentService
from app.services.referral_service import ReferralService

WEBHOOK_SECRET = "dev-webhook-secret"


def _sign(payload: dict, secret: str = WEBHOOK_SECRET) -> tuple[bytes, str]:
    raw = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    return raw, sig


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes — normalize to UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _pay_invoice(db, user_id: uuid.UUID, amount_usd: Decimal,
                       idem: str | None = None) -> PaymentInvoice:
    """Create an invoice for `user_id` and drive it to PAID via webhook."""
    svc = PaymentService(db, MockCryptoProvider())
    invoice = await svc.create_invoice(
        user_id=user_id, amount_usd=amount_usd, currency="USDT",
        idempotency_key=idem or f"rw-{uuid.uuid4().hex}",
    )
    raw, sig = _sign({"external_id": invoice.external_invoice_id,
                      "event": "paid"})
    event = await svc.verify_and_record_webhook(
        payload=raw, signature=sig, secret=WEBHOOK_SECRET)
    await svc.handle_event(event)
    await db.refresh(invoice)
    return invoice


@pytest_asyncio.fixture
async def referrer(db) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"ref_{uuid.uuid4().hex[:6]}@test.com",
        display_name="Referrer",
        role="student",
        status="active",
        credit_balance=Decimal("0"),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    await ReferralService(db).ensure_referral_code(s)
    await db.commit()
    return s


@pytest_asyncio.fixture
async def referred(db, referrer) -> Student:
    """A referred user with a PENDING referral row."""
    s = Student(
        id=uuid.uuid4(),
        email=f"rfd_{uuid.uuid4().hex[:6]}@test.com",
        display_name="Referred",
        role="student",
        status="active",
        credit_balance=Decimal("0"),
        referred_by_user_id=referrer.id,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    db.add(Referral(
        id=uuid.uuid4(),
        referrer_user_id=referrer.id,
        referred_user_id=s.id,
        referral_code=referrer.referral_code,
        status=ReferralStatus.PENDING,
    ))
    await db.commit()
    return s


class TestRewardQualification:
    """Lesson 7.5: qualify + schedule on payment."""

    @pytest.mark.asyncio
    async def test_no_reward_before_payment(self, db, referrer, referred):
        rewards = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.user_id == referrer.id)
        )).scalars().all()
        assert rewards == []

        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        assert referral.status == ReferralStatus.PENDING

    @pytest.mark.asyncio
    async def test_payment_qualifies_and_schedules_reward(
        self, db, referrer, referred
    ):
        invoice = await _pay_invoice(db, referred.id, Decimal("50"))

        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        assert referral.status == ReferralStatus.QUALIFIED
        assert referral.qualified_at is not None

        reward = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id)
        )).scalar_one()
        assert reward.status == RewardStatus.PENDING
        assert reward.amount == Decimal("5.00")  # 10% of 50
        assert reward.reference_invoice_id == invoice.id
        assert reward.scheduled_release_at is not None
        # Holding period ~7 days in the future.
        delta = _aware(reward.scheduled_release_at) - datetime.now(timezone.utc)
        assert timedelta(days=6) < delta <= timedelta(days=7)

    @pytest.mark.asyncio
    async def test_non_referred_payment_earns_nothing(self, db, student):
        await _pay_invoice(db, student.id, Decimal("50"))
        rewards = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.user_id == student.id)
        )).scalars().all()
        assert rewards == []

    @pytest.mark.asyncio
    async def test_duplicate_webhook_single_reward(self, db, referrer, referred):
        """Webhook replay must not create a second reward."""
        svc = PaymentService(db, MockCryptoProvider())
        invoice = await svc.create_invoice(
            user_id=referred.id, amount_usd=Decimal("50"), currency="USDT",
            idempotency_key=f"dup-{uuid.uuid4().hex}")
        raw, sig = _sign({"external_id": invoice.external_invoice_id,
                          "event": "paid"})
        event1 = await svc.verify_and_record_webhook(
            payload=raw, signature=sig, secret=WEBHOOK_SECRET)
        await svc.handle_event(event1)
        # Replay the same webhook payload.
        event2 = await svc.verify_and_record_webhook(
            payload=raw, signature=sig, secret=WEBHOOK_SECRET)
        assert event2.id == event1.id  # deduped at storage layer
        await svc.handle_event(event2)

        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        rewards = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id)
        )).scalars().all()
        assert len(rewards) == 1


class TestRewardRelease:
    """Lesson 7.5: holding period + release to credits."""

    @staticmethod
    async def _make_due(db, referral_id: uuid.UUID) -> None:
        """Backdate scheduled_release_at so the reward is due now."""
        reward = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral_id)
        )).scalar_one()
        reward.scheduled_release_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()

    @pytest.mark.asyncio
    async def test_holding_period_respected(self, db, referrer, referred):
        await _pay_invoice(db, referred.id, Decimal("50"))
        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        reward = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id)
        )).scalar_one()

        await ReferralService(db).release_due_rewards()
        await db.refresh(reward)
        await db.refresh(referral)

        # Still on hold — not released, referrer uncredited.
        assert reward.status == RewardStatus.PENDING
        assert referral.status == ReferralStatus.QUALIFIED

        referrer_bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer.id)
        )).scalar_one()
        assert Decimal(referrer_bal) == Decimal("0")

    @pytest.mark.asyncio
    async def test_reward_released_after_holding(self, db, referrer, referred):
        await _pay_invoice(db, referred.id, Decimal("50"))
        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        await self._make_due(db, referral.id)

        released = await ReferralService(db).release_due_rewards()
        assert len(released) == 1
        assert released[0].status == RewardStatus.PAID

        referrer_bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer.id)
        )).scalar_one()
        assert Decimal(referrer_bal) == Decimal("5.00")

        await db.refresh(referral)
        assert referral.status == ReferralStatus.REWARDED
        assert referral.rewarded_at is not None

    @pytest.mark.asyncio
    async def test_release_is_idempotent(self, db, referrer, referred):
        await _pay_invoice(db, referred.id, Decimal("50"))
        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        await self._make_due(db, referral.id)

        svc = ReferralService(db)
        first = await svc.release_due_rewards()
        second = await svc.release_due_rewards()  # nothing left PENDING
        assert len(first) == 1
        assert second == []

        referrer_bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer.id)
        )).scalar_one()
        assert Decimal(referrer_bal) == Decimal("5.00")

        # Exactly one ledger row for this reward.
        ledger = (await db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == f"ref-reward-{first[0].id}")
        )).scalars().all()
        assert len(ledger) == 1

    @pytest.mark.asyncio
    async def test_revoked_referral_does_not_pay(self, db, referrer, referred):
        await _pay_invoice(db, referred.id, Decimal("50"))
        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )).scalar_one()
        await self._make_due(db, referral.id)

        await ReferralService(db).revoke_referral(referral.id)
        released = await ReferralService(db).release_due_rewards()
        assert released == []

        reward = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id)
        )).scalar_one()
        assert reward.status == RewardStatus.REVOKED

        referrer_bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer.id)
        )).scalar_one()
        assert Decimal(referrer_bal) == Decimal("0")
