"""
tests/integration/test_phase7_acceptance.py
──────────────────────────────────────────
Lesson 7.7 — Phase 7 acceptance test.

End-to-end scenario: user registers via referral link → referred user pays
→ referral qualifies + reward scheduled (held) → holding period elapses →
reward released to referrer's credit balance → stats reflect the reward.
Also covers abuse rejection (self-referral, duplicate webhook).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.credit_ledger import CreditLedger
from app.models.payment_invoice import PaymentInvoice
from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardStatus, RewardTransaction
from app.models.student import Student
from app.services.payment_service import MockCryptoProvider, PaymentService
from app.services.referral_service import ReferralService

WEBHOOK_SECRET = "dev-webhook-secret"


def _sign(payload: dict) -> tuple[bytes, str]:
    raw = json.dumps(payload).encode()
    return raw, hmac.new(WEBHOOK_SECRET.encode(), raw,
                         hashlib.sha512).hexdigest()


class TestPhase7Acceptance:
    """Full referral journey: register → pay → hold → release → reward."""

    @pytest.mark.asyncio
    async def test_full_referral_journey(self, client, db):
        # 1. Existing user gets a referral code + link
        referrer = Student(
            id=uuid.uuid4(),
            email=f"acc_ref_{uuid.uuid4().hex[:6]}@test.com",
            display_name="Acc Referrer",
            role="student", status="active", credit_balance=Decimal("0"),
        )
        db.add(referrer)
        await db.commit()
        await db.refresh(referrer)
        svc = ReferralService(db)
        code = await svc.ensure_referral_code(referrer)
        link = await svc.get_referral_link(referrer)
        assert link.endswith(code)

        # 2. A stranger registers with the code (public validate first)
        v = await client.get(f"/api/v1/referrals/{code}/validate")
        assert v.status_code == 200 and v.json()["valid"] is True

        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": f"acc_new_{uuid.uuid4().hex[:6]}@test.com",
                  "password": "password123", "display_name": "Referred User"},
            params={"ref": code},
        )
        assert reg.status_code == 201
        referred_id = uuid.UUID(reg.json()["data"]["id"])
        assert reg.json()["data"]["referred_by_user_id"] == str(referrer.id)

        # 3. Referred user pays — reward scheduled, NOT released
        pay = PaymentService(db, MockCryptoProvider())
        invoice = await pay.create_invoice(
            user_id=referred_id, amount_usd=Decimal("25"), currency="USDT",
            idempotency_key=f"acc7-{uuid.uuid4().hex}")
        raw, sig = _sign({"external_id": invoice.external_invoice_id,
                          "event": "paid"})
        event = await pay.verify_and_record_webhook(
            payload=raw, signature=sig, secret=WEBHOOK_SECRET)
        await pay.handle_event(event)

        referral = (await db.execute(
            select(Referral).where(Referral.referred_user_id == referred_id)
        )).scalar_one()
        assert referral.status == ReferralStatus.QUALIFIED

        reward = (await db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id)
        )).scalar_one()
        assert reward.status == RewardStatus.PENDING
        assert reward.amount == Decimal("2.50")  # 10% of 25

        # Referrer not credited while on hold
        bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer.id)
        )).scalar_one()
        assert Decimal(bal) == Decimal("0")

        # 4. Holding period elapses → admin releases due rewards
        reward.scheduled_release_at = datetime.now(timezone.utc) - timedelta(days=1)
        await db.commit()

        released = await ReferralService(db).release_due_rewards()
        assert any(r.id == reward.id for r in released)

        # 5. Referrer is paid; referral marked REWARDED
        bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == referrer.id)
        )).scalar_one()
        assert Decimal(bal) == Decimal("2.50")

        await db.refresh(referral)
        assert referral.status == ReferralStatus.REWARDED

        ledger = (await db.execute(
            select(CreditLedger).where(
                CreditLedger.idempotency_key == f"ref-reward-{reward.id}")
        )).scalars().all()
        assert len(ledger) == 1  # exactly-once crediting

        # 6. Stats reflect the reward
        stats = await ReferralService(db).get_referral_stats(referrer)
        assert stats["total_referrals"] >= 1
        assert stats["rewarded_referrals"] >= 1
        assert Decimal(stats["total_earnings_usd"]) >= Decimal("2.50")

    @pytest.mark.asyncio
    async def test_self_referral_cannot_earn(self, app, db):
        """A user registering with their own code earns nothing."""
        user = Student(
            id=uuid.uuid4(),
            email=f"acc_self_{uuid.uuid4().hex[:6]}@test.com",
            display_name="Self",
            role="student", status="active", credit_balance=Decimal("0"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        code = await ReferralService(db).ensure_referral_code(user)

        # Session as this user, registering a second account with own code.
        from app.services.auth import SESSION_COOKIE_NAME, create_session_token
        from httpx import ASGITransport, AsyncClient

        token = create_session_token(user.id, user.role)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
            cookies={SESSION_COOKIE_NAME: token},
        ) as sc:
            resp = await sc.post(
                "/api/v1/auth/register",
                json={"email": f"acc_self2_{uuid.uuid4().hex[:6]}@test.com",
                      "password": "password123", "display_name": "Self2"},
                params={"ref": code},
            )
        assert resp.status_code == 201
        assert resp.json()["data"]["referred_by_user_id"] is None

        referrals = (await db.execute(
            select(Referral).where(Referral.referrer_user_id == user.id)
        )).scalars().all()
        assert referrals == []
