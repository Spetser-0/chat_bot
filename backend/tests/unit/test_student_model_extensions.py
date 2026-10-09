"""
tests/unit/test_student_model_extensions.py
────────────────────────────────────────────
Unit tests for Phase 1 Student model extensions.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.student import Student, StudentRole


class TestStudentReferralFields:
    """Test referral system fields."""

    async def test_student_can_have_referral_code(self, db):
        """Test student can have unique referral code."""
        student = Student(
            id=uuid.uuid4(),
            email="referrer@example.com",
            referral_code="SPETSER-ABC123",
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.referral_code == "SPETSER-ABC123"

    async def test_referral_code_must_be_unique(self, db):
        """Test referral code uniqueness constraint."""
        student1 = Student(
            id=uuid.uuid4(),
            email="user1@example.com",
            referral_code="SPETSER-SAME",
        )
        db.add(student1)
        await db.commit()

        student2 = Student(
            id=uuid.uuid4(),
            email="user2@example.com",
            referral_code="SPETSER-SAME",
        )
        db.add(student2)

        with pytest.raises(IntegrityError):
            await db.commit()

    async def test_student_can_have_referrer(self, db):
        """Test student can be referred by another student."""
        referrer = Student(
            id=uuid.uuid4(),
            email="referrer@example.com",
            referral_code="SPETSER-REF123",
        )
        db.add(referrer)
        await db.flush()

        referred = Student(
            id=uuid.uuid4(),
            email="referred@example.com",
            referred_by_user_id=referrer.id,
        )
        db.add(referred)
        await db.commit()

        await db.refresh(referred)
        assert referred.referred_by_user_id == referrer.id

    async def test_referrer_deletion_nullifies_referral(self, db):
        """Test that deleting referrer sets referred_by_user_id to NULL."""
        referrer = Student(
            id=uuid.uuid4(),
            email="referrer@example.com",
        )
        db.add(referrer)
        await db.flush()

        referred = Student(
            id=uuid.uuid4(),
            email="referred@example.com",
            referred_by_user_id=referrer.id,
        )
        db.add(referred)
        await db.commit()

        # Delete referrer
        await db.delete(referrer)
        await db.commit()

        await db.refresh(referred)
        assert referred.referred_by_user_id is None


class TestStudentPremiumFields:
    """Test premium subscription fields."""

    async def test_student_defaults_to_non_premium(self, db):
        """Test is_premium defaults to False."""
        student = Student(
            id=uuid.uuid4(),
            email="user@example.com",
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.is_premium is False
        assert student.premium_expires_at is None

    async def test_student_can_be_premium(self, db):
        """Test student can be set to premium with expiration."""
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        student = Student(
            id=uuid.uuid4(),
            email="premium@example.com",
            is_premium=True,
            premium_expires_at=expiry,
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.is_premium is True
        assert student.premium_expires_at is not None
        # SQLite returns naive datetimes even for DateTime(timezone=True);
        # normalize both sides to UTC-aware before comparing.
        stored = student.premium_expires_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert (stored - expiry).total_seconds() < 1

    async def test_premium_expiration_can_be_null(self, db):
        """Test premium can have no expiration (lifetime)."""
        student = Student(
            id=uuid.uuid4(),
            email="lifetime@example.com",
            is_premium=True,
            premium_expires_at=None,
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.is_premium is True
        assert student.premium_expires_at is None


class TestStudentSecurityFields:
    """Test security and account protection fields."""

    async def test_failed_login_attempts_defaults_to_zero(self, db):
        """Test failed_login_attempts defaults to 0."""
        student = Student(
            id=uuid.uuid4(),
            email="user@example.com",
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.failed_login_attempts == 0
        assert student.locked_until is None

    async def test_can_increment_failed_login_attempts(self, db):
        """Test failed login attempts can be incremented."""
        unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        student = Student(
            id=uuid.uuid4(),
            email=unique_email,
            failed_login_attempts=0,
        )
        db.add(student)
        await db.commit()

        # Simulate failed login
        student.failed_login_attempts += 1
        await db.commit()

        await db.refresh(student)
        assert student.failed_login_attempts == 1

    async def test_account_can_be_locked(self, db):
        """Test account can be locked with locked_until timestamp."""
        lockout_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        unique_email = f"locked_{uuid.uuid4().hex[:8]}@example.com"
        student = Student(
            id=uuid.uuid4(),
            email=unique_email,
            failed_login_attempts=5,
            locked_until=lockout_time,
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.failed_login_attempts == 5
        assert student.locked_until is not None
        # SQLite doesn't store timezone info. We compare as naive.
        assert student.locked_until.replace(tzinfo=None) > datetime.now(timezone.utc).replace(tzinfo=None)


    async def test_last_login_ip_can_be_stored(self, db):
        """Test last login IP address can be stored."""
        student = Student(
            id=uuid.uuid4(),
            email="user@example.com",
            last_login_ip="192.168.1.100",
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.last_login_ip == "192.168.1.100"

    async def test_last_login_ip_supports_ipv6(self, db):
        """Test last login IP supports IPv6 addresses."""
        ipv6_address = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        student = Student(
            id=uuid.uuid4(),
            email="ipv6@example.com",
            last_login_ip=ipv6_address,
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.last_login_ip == ipv6_address


class TestStudentRoleExtension:
    """Test SUPERADMIN role addition."""

    async def test_superadmin_role_exists(self):
        """Test SUPERADMIN role constant exists."""
        assert hasattr(StudentRole, "SUPERADMIN")
        assert StudentRole.SUPERADMIN == "superadmin"

    async def test_student_can_have_superadmin_role(self, db):
        """Test student can be assigned superadmin role."""
        student = Student(
            id=uuid.uuid4(),
            email="superadmin@example.com",
            role=StudentRole.SUPERADMIN,
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.role == "superadmin"


class TestStudentExtensionsIntegration:
    """Test all extensions work together."""

    async def test_complete_student_with_all_new_fields(self, db):
        """Test student with all Phase 1 fields."""
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        student = Student(
            id=uuid.uuid4(),
            email="complete@example.com",
            role=StudentRole.SUPERADMIN,
            # Referral fields
            referral_code="SPETSER-FULL",
            referred_by_user_id=None,
            # Premium fields
            is_premium=True,
            premium_expires_at=expiry,
            # Security fields
            failed_login_attempts=0,
            locked_until=None,
            last_login_ip="203.0.113.42",
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.email == "complete@example.com"
        assert student.role == "superadmin"
        assert student.referral_code == "SPETSER-FULL"
        assert student.is_premium is True
        assert student.premium_expires_at is not None
        assert student.failed_login_attempts == 0
        assert student.last_login_ip == "203.0.113.42"

    async def test_existing_fields_still_work(self, db):
        """Test that existing Student fields still work after extension."""
        student = Student(
            id=uuid.uuid4(),
            email="existing@example.com",
            display_name="Test User",
            role=StudentRole.STUDENT,
            status="active",
            credit_balance=Decimal("100.0"),
        )
        db.add(student)
        await db.commit()

        await db.refresh(student)
        assert student.display_name == "Test User"
        assert student.role == "student"
        assert student.status == "active"
        assert student.credit_balance == Decimal("100.0")
