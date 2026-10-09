"""
tests/unit/test_referral_service.py
────────────────────────────────────
Unit tests for ReferralService (Lesson 7.1).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import ConflictError
from app.db.session import Base
from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardTransaction, RewardStatus
from app.models.student import Student
from app.services.referral_service import ReferralService


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def student(db: AsyncSession) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"u{uuid.uuid4().hex[:6]}@test.com",
        display_name="Test Student",
        role="student",
        status="active",
        credit_balance=Decimal("100"),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest_asyncio.fixture
async def referral_service(db: AsyncSession) -> ReferralService:
    return ReferralService(db)


class TestGenerateUniqueCode:
    @pytest.mark.asyncio
    async def test_generates_formatted_code(self, referral_service: ReferralService):
        code = await referral_service.generate_unique_code()
        assert code.startswith("SPETSER-")
        assert len(code) == len("SPETSER-") + 6  # SPETSER- + 6 chars

    @pytest.mark.asyncio
    async def test_code_is_unique(self, referral_service: ReferralService, db: AsyncSession):
        code1 = await referral_service.generate_unique_code()
        code2 = await referral_service.generate_unique_code()
        assert code1 != code2

    @pytest.mark.asyncio
    async def test_code_format(self, referral_service: ReferralService):
        code = await referral_service.generate_unique_code()
        parts = code.split("-")
        assert len(parts) == 2
        assert parts[0] == "SPETSER"
        assert len(parts[1]) == 6
        assert parts[1].isalnum()
        assert parts[1].isupper()


class TestEnsureReferralCode:
    @pytest.mark.asyncio
    async def test_creates_code_when_missing(self, referral_service: ReferralService, student: Student):
        assert student.referral_code is None
        code = await referral_service.ensure_referral_code(student)
        assert code.startswith("SPETSER-")
        await referral_service._db.refresh(student)
        assert student.referral_code == code

    @pytest.mark.asyncio
    async def test_returns_existing_code(self, referral_service: ReferralService, student: Student, db: AsyncSession):
        # First ensure code exists
        code = await referral_service.ensure_referral_code(student)
        # Call again - should return same code
        code2 = await referral_service.ensure_referral_code(student)
        assert code == code2


class TestValidateReferralCode:
    @pytest.mark.asyncio
    async def test_valid_code_returns_referrer(self, referral_service: ReferralService, student: Student, db: AsyncSession):
        code = await referral_service.ensure_referral_code(student)
        referrer = await referral_service.validate_referral_code(code)
        assert referrer is not None
        assert referrer.id == student.id

    @pytest.mark.asyncio
    async def test_invalid_code_returns_none(self, referral_service: ReferralService):
        referrer = await referral_service.validate_referral_code("SPETSER-INVALID")
        assert referrer is None

    @pytest.mark.asyncio
    async def test_wrong_prefix_returns_none(self, referral_service: ReferralService):
        referrer = await referral_service.validate_referral_code("WRONG-ABCDEF")
        assert referrer is None

    @pytest.mark.asyncio
    async def test_empty_code_returns_none(self, referral_service: ReferralService):
        referrer = await referral_service.validate_referral_code("")
        assert referrer is None

    @pytest.mark.asyncio
    async def test_none_code_returns_none(self, referral_service: ReferralService):
        referrer = await referral_service.validate_referral_code(None)
        assert referrer is None


class TestGetReferralLink:
    @pytest.mark.asyncio
    async def test_returns_full_url(self, referral_service: ReferralService, student: Student):
        link = await referral_service.get_referral_link(student)
        assert link.startswith("https://spetser.ai/r/SPETSER-")
        assert student.referral_code in link

    @pytest.mark.asyncio
    async def test_custom_base_url(self, referral_service: ReferralService, student: Student):
        link = await referral_service.get_referral_link(student, base_url="https://custom.domain")
        assert link.startswith("https://custom.domain/r/SPETSER-")


class TestGetReferralStats:
    @pytest.mark.asyncio
    async def test_returns_zero_for_new_user(self, referral_service: ReferralService, student: Student):
        stats = await referral_service.get_referral_stats(student)
        assert stats["total_referrals"] == 0
        assert stats["qualified_referrals"] == 0
        assert stats["rewarded_referrals"] == 0
        assert stats["total_earnings_usd"] == "0"
        assert stats["referral_link"].startswith("https://spetser.ai/r/")

    @pytest.mark.asyncio
    async def test_counts_referrals_correctly(self, referral_service: ReferralService, student: Student, db: AsyncSession):
        # Create some referrals
        for i in range(3):
            ref = Referral(
                id=uuid.uuid4(),
                referrer_user_id=student.id,
                referred_user_id=uuid.uuid4(),
                referral_code=student.referral_code or "SPETSER-TEST",
                status=ReferralStatus.QUALIFIED if i < 2 else ReferralStatus.REWARDED,
            )
            db.add(ref)
        await db.commit()

        stats = await referral_service.get_referral_stats(student)
        assert stats["total_referrals"] == 3
        assert stats["qualified_referrals"] == 2
        assert stats["rewarded_referrals"] == 1


class TestGenerateUniqueCodeCollision:
    @pytest.mark.asyncio
    async def test_handles_collision(self, referral_service: ReferralService, db: AsyncSession, student: Student):
        # Generate a code
        code = await referral_service.generate_unique_code()
        
        # Manually create a student with that code to force collision
        other = Student(
            id=uuid.uuid4(),
            email=f"other{uuid.uuid4().hex[:6]}@test.com",
            role="student",
            status="active",
            credit_balance=0,
            referral_code=code,
        )
        db.add(other)
        await db.commit()

        # Next generation should produce a different code
        new_code = await referral_service.generate_unique_code()
        assert new_code != code
        assert new_code.startswith("SPETSER-")

class TestCheckFraud:
    """Anti-fraud checks (Lesson 7.4)."""

    @pytest.mark.asyncio
    async def test_self_referral_rejected(
        self, referral_service: ReferralService, student: Student
    ):
        with pytest.raises(Exception) as exc:
            await referral_service._check_fraud(
                referrer=student, referred_user=student
            )
        assert "self-referral" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_duplicate_referral_rejected(
        self, referral_service: ReferralService, db: AsyncSession, student: Student
    ):
        other = Student(
            id=uuid.uuid4(),
            email=f"o{uuid.uuid4().hex[:6]}@test.com",
            role="student",
            status="active",
            credit_balance=0,
        )
        db.add(other)
        await db.commit()
        await db.refresh(other)

        code = await referral_service.ensure_referral_code(student)

        db.add(
            Referral(
                id=uuid.uuid4(),
                referrer_user_id=student.id,
                referred_user_id=other.id,
                referral_code=code,
                status=ReferralStatus.PENDING,
            )
        )
        await db.commit()

        with pytest.raises(Exception) as exc:
            await referral_service._check_fraud(
                referrer=student, referred_user=other
            )
        assert "already been referred" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_disposable_email_rejected(
        self, referral_service: ReferralService, db: AsyncSession, student: Student
    ):
        throwaway = Student(
            id=uuid.uuid4(),
            email=f"throw{uuid.uuid4().hex[:6]}@mailinator.com",
            role="student",
            status="active",
            credit_balance=0,
        )
        db.add(throwaway)
        await db.commit()
        await db.refresh(throwaway)

        with pytest.raises(Exception) as exc:
            await referral_service._check_fraud(
                referrer=student, referred_user=throwaway
            )
        assert "disposable" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_device_fingerprint_collision_rejected(
        self, referral_service: ReferralService, db: AsyncSession, student: Student
    ):
        fp = f"fp-{uuid.uuid4().hex}"
        other = Student(
            id=uuid.uuid4(),
            email=f"fp{uuid.uuid4().hex[:6]}@test.com",
            role="student",
            status="active",
            credit_balance=0,
        )
        db.add(other)
        await db.commit()
        await db.refresh(other)

        code = await referral_service.ensure_referral_code(student)

        db.add(
            Referral(
                id=uuid.uuid4(),
                referrer_user_id=student.id,
                referred_user_id=other.id,
                referral_code=code,
                status=ReferralStatus.PENDING,
                device_fingerprint=fp,
            )
        )
        await db.commit()

        third = Student(
            id=uuid.uuid4(),
            email=f"fp2{uuid.uuid4().hex[:6]}@test.com",
            role="student",
            status="active",
            credit_balance=0,
        )
        db.add(third)
        await db.commit()
        await db.refresh(third)

        with pytest.raises(Exception) as exc:
            await referral_service._check_fraud(
                referrer=student, referred_user=third, device_fingerprint=fp
            )
        assert "fingerprint" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_ip_rate_limit_rejected(
        self, referral_service: ReferralService, db: AsyncSession, student: Student
    ):
        ip = "203.0.113.7"
        code = await referral_service.ensure_referral_code(student)
        for _ in range(ReferralService.MAX_REFERRALS_PER_IP_PER_DAY):
            u = Student(
                id=uuid.uuid4(),
                email=f"ip{uuid.uuid4().hex[:6]}@test.com",
                role="student",
                status="active",
                credit_balance=0,
            )
            db.add(u)
            await db.commit()
            await db.refresh(u)
            db.add(
                Referral(
                    id=uuid.uuid4(),
                    referrer_user_id=student.id,
                    referred_user_id=u.id,
                    referral_code=code,
                    status=ReferralStatus.PENDING,
                    ip_address=ip,
                )
            )
            await db.commit()

        extra = Student(
            id=uuid.uuid4(),
            email=f"ipx{uuid.uuid4().hex[:6]}@test.com",
            role="student",
            status="active",
            credit_balance=0,
        )
        db.add(extra)
        await db.commit()
        await db.refresh(extra)

        with pytest.raises(Exception) as exc:
            await referral_service._check_fraud(
                referrer=student, referred_user=extra, ip_address=ip
            )
        assert "ip address" in str(exc.value).lower()
