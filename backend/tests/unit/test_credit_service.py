"""
tests/unit/test_credit_service.py
──────────────────────────────────
Lesson 5.1 — wallet layer: spend/add/refund, balance_after ledger,
idempotency, cost formula. Concurrency: guarded UPDATE (rowcount)==1.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import InsufficientCreditsError, ValidationError
from app.core.security import encrypt_secret
from app.db.session import Base
from app.models.ai_provider import AIProvider
from app.models.credit_ledger import CreditLedger
from app.models.skill import Skill
from app.models.student import Student
from app.services.credit_service import CreditService


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _student(db, balance="100.0000") -> Student:
    s = Student(id=uuid.uuid4(), email=f"u{uuid.uuid4().hex[:6]}@t.com",
                role="student", status="active",
                credit_balance=Decimal(balance), is_premium=False)
    db.add(s)
    await db.commit()
    return s


class TestSpendAndBalance:
    @pytest.mark.asyncio
    async def test_spend_records_balance_after(self, db):
        s = await _student(db, "50.0000")
        await CreditService(db, s).spend_credits(Decimal("10"), description="chat")
        assert (await CreditService(db, s).get_balance()) == Decimal("40.0000")
        row = (await db.execute(select(CreditLedger))).scalar_one()
        assert row.balance_after == Decimal("40.0000")
        assert row.entry_type == "charge"
        assert row.credits_charged == Decimal("10.0000")

    @pytest.mark.asyncio
    async def test_cannot_spend_more_than_balance(self, db):
        s = await _student(db, "5.0000")
        sid = s.id  # rollback below expires `s`; keep the UUID handy
        with pytest.raises(InsufficientCreditsError):
            await CreditService(db, s).spend_credits(Decimal("10"))
        # balance unchanged after failed spend
        bal = (await db.execute(
            select(Student.credit_balance).where(Student.id == sid)
        )).scalar_one()
        assert bal == Decimal("5.0000")

    @pytest.mark.asyncio
    async def test_zero_spend_rejected(self, db):
        s = await _student(db)
        with pytest.raises(ValidationError):
            await CreditService(db, s).spend_credits(Decimal("0"))

    @pytest.mark.asyncio
    async def test_add_and_refund(self, db):
        s = await _student(db, "10.0000")
        svc = CreditService(db, s)
        await svc.add_credits(Decimal("25"), description="topup")
        await svc.refund_credits(Decimal("5"))
        assert (await svc.get_balance()) == Decimal("40.0000")
        types = [r.entry_type for r in (await db.execute(select(CreditLedger))).scalars()]
        assert types == ["topup", "refund"]


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_spend_replay_is_noop(self, db):
        s = await _student(db, "100.0000")
        svc = CreditService(db, s)
        key = f"pay-{uuid.uuid4()}"
        await svc.spend_credits(Decimal("10"), idempotency_key=key)
        again = await svc.spend_credits(Decimal("10"), idempotency_key=key)
        assert again == Decimal("10.0000")
        assert (await svc.get_balance()) == Decimal("90.0000")
        rows = (await db.execute(select(CreditLedger))).scalars().all()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_topup_replay_is_noop(self, db):
        s = await _student(db, "0.0000")
        svc = CreditService(db, s)
        key = f"hook-{uuid.uuid4()}"
        await svc.add_credits(Decimal("50"), idempotency_key=key)
        await svc.add_credits(Decimal("50"), idempotency_key=key)
        assert (await svc.get_balance()) == Decimal("50.0000")


class TestCostFormula:
    @pytest.fixture
    def provider(self):
        return AIProvider(
            id=uuid.uuid4(), slug="p", name="P", model_name="m",
            api_key_encrypted="enc", cost_input_per_1k=Decimal("0.010"),
            cost_output_per_1k=Decimal("0.030"),
        )

    def test_cost_without_skill(self, provider):
        svc = CreditService(None, None)
        import asyncio
        cost = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            svc.calculate_message_cost(provider, input_tokens=1000, output_tokens=500)
        )
        # (1×0.010 + 0.5×0.030) × 100 = (0.010+0.015)×100 = 2.5
        assert cost == Decimal("2.5000")

    @pytest.mark.asyncio
    async def test_cost_with_multiplier(self, provider, db):
        skill = Skill(id=uuid.uuid4(), name="s", slug=f"s-{uuid.uuid4().hex[:6]}",
                      system_prompt="x", cost_multiplier=Decimal("2"))
        svc = CreditService(db, None)
        cost = await svc.calculate_message_cost(
            provider, input_tokens=1000, output_tokens=0, skill=skill)
        assert cost == Decimal("2.0000")  # 0.010×100×2


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_parallel_spends_never_go_negative(self):
        """20 parallel spends of 10 on a 100 balance: exactly 10 succeed.

        SQLite serializes writers (file DB + WAL + busy timeout), which for
        our guarded UPDATE means each (balance check + ledger) is atomic —
        total charged == 100, balance ends at exactly 0, races denied.
        """
        import asyncio
        import os
        import tempfile
        from collections import Counter

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{path}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import async_sessionmaker

        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(text("PRAGMA journal_mode=WAL"))
            maker = async_sessionmaker(engine, class_=AsyncSession,
                                       expire_on_commit=False)
            async with maker() as s:
                stu = Student(id=uuid.uuid4(),
                              email=f"par{uuid.uuid4().hex[:6]}@t.com",
                              role="student", status="active",
                              credit_balance=Decimal("100"), is_premium=False)
                s.add(stu)
                await s.commit()
                sid = stu.id

            async def spend(i: int) -> str:
                async with maker() as s:
                    fresh = (await s.execute(
                        select(Student).where(Student.id == sid))).scalar_one()
                    try:
                        await CreditService(s, fresh).spend_credits(Decimal("10"))
                        return "ok"
                    except InsufficientCreditsError:
                        return "denied"
                    except Exception:
                        return "error"

            rs = await asyncio.gather(*(spend(i) for i in range(20)))
            counts = Counter(rs)
            assert counts["error"] == 0
            assert counts["ok"] == 10
            assert counts["denied"] == 10

            async with maker() as s:
                bal = (await s.execute(
                    select(Student.credit_balance).where(Student.id == sid)
                )).scalar_one()
            assert bal == Decimal("0.0000")
        finally:
            await engine.dispose()
            os.unlink(path)
