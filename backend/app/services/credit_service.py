"""
app/services/credit_service.py
───────────────────────────────
Wallet-facing credit service (Phase 5, Lesson 5.1).

Scope note: this service is the generic WALLET layer (balance, spend,
top-up, refunds, admin adjustments) used by chat and payments. The
request-scoped reserve/capture pipeline for presentations lives in
`app/services/credit.py` and is intentionally untouched.

Design rules:
- Every balance mutation writes a CreditLedger row with `balance_after`.
- All mutations lock the student row (SELECT … FOR UPDATE) → no lost
  updates under concurrent requests.
- Idempotency: callers MUST pass a stable key for retries/webhooks.
  Repeats are no-ops returning the original outcome.
- Balance can NEVER go negative (Lesson 5.4 rule); admin overrides are
  an intentionally different method (add_credits) so audit trails show
  them separately.

Conversion: 1 USD = 100 credits (matches legacy credit.py pricing).
"""
from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InsufficientCreditsError, ValidationError
from app.models.ai_provider import AIProvider
from app.models.credit_ledger import CreditLedger, LedgerEntryType
from app.models.skill import Skill
from app.models.student import Student

CREDITS_PER_USD = Decimal("100")
_Q = Decimal("0.0001")  # ledger precision (18,4)


def _q(v: Decimal) -> Decimal:
    return v.quantize(_Q, rounding=ROUND_HALF_UP)


class CreditService:
    """Generic wallet operations for one student (or any target by id)."""

    def __init__(self, db: AsyncSession, student: Student) -> None:
        self._db = db
        self._student = student

    # ── Read ───────────────────────────────────────────────────────────
    async def get_balance(self) -> Decimal:
        return _q(self._student.credit_balance)

    async def get_history(self, *, limit: int = 100, offset: int = 0) -> list[CreditLedger]:
        result = await self._db.execute(
            select(CreditLedger)
            .where(CreditLedger.student_id == self._student.id)
            .order_by(CreditLedger.created_at.desc())
            .offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    # ── Cost math (Lesson 5.2) ─────────────────────────────────────────
    async def calculate_message_cost(
        self,
        provider: AIProvider,
        *,
        input_tokens: int,
        output_tokens: int,
        skill: Skill | None = None,
    ) -> Decimal:
        """credits = (in/1000*rate_in + out/1000*rate_out) × multiplier × 100."""
        usd = (
            Decimal(input_tokens) / 1000 * provider.cost_input_per_1k
            + Decimal(output_tokens) / 1000 * provider.cost_output_per_1k
        )
        multiplier = skill.cost_multiplier if skill is not None else Decimal("1")
        return _q(usd * multiplier * CREDITS_PER_USD)

    # ── Mutations (each writes a ledger row with balance_after) ────────
    async def assert_enough_credits(self, needed: Decimal) -> None:
        """Read-only check; no lock. Raise InsufficientCreditsError when short."""
        if needed < 0:
            raise ValidationError("المبلغ لا يمكن أن يكون سالبًا.")
        if self._student.credit_balance < needed:
            raise InsufficientCreditsError("الرصيد غير كافٍ.")

    async def spend_credits(
        self, amount: Decimal, *, description: str = "",
        reference_type: str | None = None, reference_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> Decimal:
        """Atomic spend: guarded UPDATE + ledger row in one transaction."""
        return await self._transact(
            amount, LedgerEntryType.CHARGE, description=description,
            reference_type=reference_type, reference_id=reference_id,
            idempotency_key=idempotency_key,
        )

    async def add_credits(
        self, amount: Decimal, *, entry_type: str = LedgerEntryType.TOPUP,
        description: str = "", reference_type: str | None = None,
        reference_id: uuid.UUID | None = None, idempotency_key: str | None = None,
    ) -> Decimal:
        """Add credits (topup / refund / referral_reward / admin_adjustment / grant)."""
        return await self._transact(
            -abs(amount), entry_type, description=description,
            reference_type=reference_type, reference_id=reference_id,
            idempotency_key=idempotency_key,
        )

    # ── Internals ──────────────────────────────────────────────────────
    async def _transact(
        self, amount: Decimal, entry_type: str, *, description: str,
        reference_type: str | None, reference_id: uuid.UUID | None,
        idempotency_key: str | None, allow_negative: bool = False,
    ) -> Decimal:
        """`amount` is a POSITIVE sp-positive debit; negative ⇒ credit.

        Idempotent: repeats with the same key return the stored value
        without touching balance or ledger.
        """
        if amount == 0:
            raise ValidationError("المبلغ لا يمكن أن يكون صفرًا.")
        if idempotency_key:
            existing = await self._db.execute(
                select(CreditLedger).where(
                    CreditLedger.idempotency_key == idempotency_key)
            )
            if (row := existing.scalar_one_or_none()) is not None:
                return row.credits_charged  # exact replay

        await self._lock_student()

        if amount > 0:
            if allow_negative:
                # Admin override: unconditional decrement (documented audit
                # path); never used for regular chat/payment flows.
                result = await self._db.execute(
                    update(Student)
                    .where(Student.id == self._student.id)
                    .values(credit_balance=Student.credit_balance - amount)
                )
            else:
                # Guarded decrement — DB-side balance check beats the race.
                result = await self._db.execute(
                    update(Student)
                    .where(Student.id == self._student.id,
                           Student.credit_balance >= amount)
                    .values(credit_balance=Student.credit_balance - amount)
                )
            if result.rowcount != 1:
                await self._db.rollback()
                # Rollback expires ORM instance; refresh so later reads
                # (get_balance etc.) stay async-safe after a failed spend.
                try:
                    await self._db.refresh(self._student)
                except Exception:
                    pass
                raise InsufficientCreditsError("الرصيد غير كافٍ.")
        else:
            await self._db.execute(
                update(Student)
                .where(Student.id == self._student.id)
                .values(credit_balance=Student.credit_balance + abs(amount))
            )

        fresh = await self._db.execute(
            select(Student.credit_balance).where(Student.id == self._student.id)
        )
        balance_after = fresh.scalar_one()
        self._student.credit_balance = balance_after  # keep session in sync

        entry = CreditLedger(
            id=uuid.uuid4(), student_id=self._student.id,
            credits_charged=_q(abs(amount)), balance_after=_q(balance_after),
            entry_type=entry_type, description=description or None,
            reference_type=reference_type, reference_id=reference_id,
            idempotency_key=idempotency_key,
        )
        self._db.add(entry)
        await self._db.commit()
        return _q(abs(amount))

    async def refund_credits(
        self, amount: Decimal, *, reference_id: uuid.UUID | None = None,
        idempotency_key: str | None = None, description: str = "استرداد",
    ) -> Decimal:
        return await self.add_credits(
            amount, entry_type=LedgerEntryType.REFUND, description=description,
            reference_type="chat", reference_id=reference_id,
            idempotency_key=idempotency_key,
        )

    # ── Admin override (Lesson 5.4) ────────────────────────────────────
    async def admin_adjust_credits(
        self,
        delta: Decimal,
        *,
        admin: Student,
        reason: str,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> Decimal:
        """Manual balance adjustment by an admin.

        Unlike assert_enough_credits, NEGATIVE results are NOT blocked here
        (admin overrides are the documented exception), but every call
        writes an AuditLog row linking ADMIN → TARGET so a negative drift
        is always attributable.
        """
        from app.models.audit_log import AuditLog

        if not reason.strip():
            raise ValidationError("سبب التعديل مطلوب.")

        balance_before = self._student.credit_balance
        result = await self._transact(
            delta, LedgerEntryType.ADMIN_ADJUSTMENT,
            description=f"admin_adjust: {reason}",
            reference_type="admin", reference_id=admin.id,
            idempotency_key=idempotency_key,
            allow_negative=True,
        )

        self._db.add(AuditLog(
            id=uuid.uuid4(),
            actor_id=admin.id,
            action="credit.admin_adjust",
            resource_type="student",
            resource_id=str(self._student.id),
            metadata_json={
                "delta": str(delta),
                "balance_before": str(balance_before),
                "reason": reason,
            },
            correlation_id=correlation_id,
        ))
        await self._db.commit()
        return result

    async def _lock_student(self) -> None:
        await self._db.execute(
            select(Student).where(Student.id == self._student.id).with_for_update()
        )
