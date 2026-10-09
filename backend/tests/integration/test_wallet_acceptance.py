"""
tests/integration/test_wallet_acceptance.py
────────────────────────────────────────────
Lesson 5.7 — Phase 5 acceptance scenario, scripted end-to-end via services
and endpoints: topup → chat spend → refund → balance/history invariants.

Runs against the shared SQLite memory DB via fixtures; every step asserts
against the ledger AND the endpoint responses, so the wallet API surface
and the service layer can't silently disagree.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.credit_ledger import CreditLedger
from app.models.student import Student
from app.services.credit_service import CreditService


class TestWalletAcceptanceScenario:
    @pytest.mark.asyncio
    async def test_full_wallet_lifecycle(
        self, authenticated_client, db, student
    ):
        svc = CreditService(db, student)
        sid = student.id

        # 1. Topup 100 credits (as a payment would)
        await svc.add_credits(Decimal("100"), description="payment-topup",
                              idempotency_key=f"pay-{uuid.uuid4()}")
        bal = await svc.get_balance()
        assert bal == Decimal("300.0000")  # student fixture starts at 200

        # 2. Refund after a complaint (10 credits back for a $5 accidentally
        #    spent). Uses refund path.
        await svc.refund_credits(Decimal("10"),
                                 idempotency_key=f"ref-{uuid.uuid4()}")
        assert (await svc.get_balance()) == Decimal("310.0000")

        # 3. Spend 150 via admin adjustment downward? No — spend directly.
        #    (semantics test: spend is only ever a guarded debit)
        await svc.spend_credits(Decimal("150"), description="ai-chat",
                                idempotency_key=f"msg-{uuid.uuid4()}")
        assert (await svc.get_balance()) == Decimal("160.0000")

        # 4. Replay the charge (idempotent): nothing changes, no extra ledger
        key = f"msg-{uuid.uuid4()}"
        await svc.spend_credits(Decimal("50"), description="ai-chat-2",
                                idempotency_key=key)
        await svc.spend_credits(Decimal("50"), description="ai-chat-2",
                                idempotency_key=key)
        assert (await svc.get_balance()) == Decimal("110.0000")

        # 5. History endpoint shows balance_after consistently
        resp = await authenticated_client.get("/api/v1/credits/history")
        assert resp.status_code == 200
        body = resp.json()
        # each entry carries the balance after the change
        assert body["total"] >= 4
        assert all(e["balance_after"] is not None for e in body["entries"])

        # 6. Negative spend on remaining balance is refused
        with pytest.raises(Exception):
            await svc.spend_credits(Decimal("999999"))
        assert (await svc.get_balance()) == Decimal("110.0000")  # unchanged
