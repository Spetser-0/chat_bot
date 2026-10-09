"""
app/services/referral_service.py
─────────────────────────────────
Referral code generation and management service (Phase 7, Lesson 7.1, 7.4).

Child analogy: every student gets a unique invitation card with a special code.
When a friend uses that card to join and later pays, the card owner gets a reward.
Anti-fraud measures prevent abuse of the referral system.
"""
from __future__ import annotations

import random
import string
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import (
    RewardStatus,
    RewardTransaction,
    RewardType,
)
from app.models.student import Student

if TYPE_CHECKING:
    from app.models.payment_invoice import PaymentInvoice


class ReferralService:
    """Service for generating and managing referral codes."""

    # Format: SPETSER-XXXXXX (6 alphanumeric chars)
    PREFIX = "SPETSER"
    CODE_LENGTH = 6
    MAX_ATTEMPTS = 10

    # Anti-fraud settings
    DISPOSABLE_EMAIL_DOMAINS = frozenset({
        "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
        "throwawaymail.com", "fakeinbox.com", "trashmail.com", "maildrop.cc",
        "yopmail.com", "temp-mail.org", "getnada.com", "dispostable.com",
        "emailondeck.com", "spamgourmet.com", "mintemail.com", "deadaddress.com",
        "fakeinbox.net", "snapmail.cc", "mytrashmail.com", "sharklasers.com",
        "grr.la", "guerrillamail.biz", "guerrillamail.net", "guerrillamail.org",
    })
    
    # Holding period for rewards (7 days)
    REWARD_HOLDING_DAYS = 7
    
    # Max referrals per referrer per payment (anti-fraud)
    MAX_REFERRALS_PER_PAYMENT = 1

    # Max referrals a single referrer may create from one IP address per 24h
    MAX_REFERRALS_PER_IP_PER_DAY = 5

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _generate_code(self) -> str:
        """Generate a random alphanumeric code."""
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choices(alphabet, k=self.CODE_LENGTH))

    def _format_code(self, code: str) -> str:
        """Format code as SPETSER-XXXXXX."""
        return f"{self.PREFIX}-{code}"

    async def _is_code_unique(self, code: str) -> bool:
        """Check if referral code is already in use."""
        result = await self._db.execute(
            select(Student.id).where(Student.referral_code == code)
        )
        return result.scalar_one_or_none() is None

    async def generate_unique_code(self) -> str:
        """Generate a unique referral code with retry logic."""
        for _ in range(self.MAX_ATTEMPTS):
            raw_code = self._generate_code()
            formatted = self._format_code(raw_code)
            if await self._is_code_unique(formatted):
                return formatted
        raise ConflictError("Unable to generate unique referral code after maximum attempts")

    async def _check_fraud(
        self,
        referrer: Student,
        referred_user: Student,
        ip_address: str | None = None,
        user_agent: str | None = None,
        landing_page_url: str | None = None,
        device_fingerprint: str | None = None,
    ) -> None:
        """
        Perform anti-fraud checks before creating a referral.
        
        Checks performed:
        1. Self-referral prevention
        2. Duplicate referral prevention (same referrer + same referred user)
        3. Already referred by someone else check
        4. Disposable email domain check
        6. Device fingerprint collision detection
        6. IP address collision detection (rate limiting)
        """
        # 1. Self-referral prevention
        if referrer.id == referred_user.id:
            raise ValidationError("Self-referral is not allowed")

        # 2. Duplicate referral prevention (same referrer + same referred user)
        existing_referral = await self._db.execute(
            select(Referral).where(
                Referral.referrer_user_id == referrer.id,
                Referral.referred_user_id == referred_user.id,
            )
        )
        if existing_referral.scalar_one_or_none() is not None:
            raise ValidationError("User has already been referred by this referrer")

        # 3. Check if referred user was already referred by someone else
        existing_referral_for_user = await self._db.execute(
            select(Referral).where(Referral.referred_user_id == referred_user.id)
        )
        if existing_referral_for_user.scalar_one_or_none() is not None:
            raise ValidationError("User has already been referred by another user")

        # 4. Disposable email domain check
        if referred_user.email:
            email_domain = referred_user.email.split("@")[-1].lower()
            if email_domain in self.DISPOSABLE_EMAIL_DOMAINS:
                raise ValidationError("Disposable email domains are not allowed for referrals")

        # 5. Device fingerprint collision detection
        if device_fingerprint:
            existing_with_fingerprint = await self._db.execute(
                select(Referral).where(
                    Referral.device_fingerprint == device_fingerprint,
                    Referral.status.in_([ReferralStatus.PENDING, ReferralStatus.QUALIFIED]),
                )
            )
            if existing_with_fingerprint.scalar_one_or_none() is not None:
                raise ValidationError("Device fingerprint already used for a referral")

        # 6. IP address rate limiting (per referrer, not global):
        #    a single referrer must not farm many referrals from the same IP in 24h.
        if ip_address:
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_same_ip = await self._db.execute(
                select(Referral).where(
                    Referral.referrer_user_id == referrer.id,
                    Referral.ip_address == ip_address,
                    Referral.created_at >= recent_cutoff,
                )
            )
            if len(recent_same_ip.scalars().all()) >= self.MAX_REFERRALS_PER_IP_PER_DAY:
                raise ValidationError("Too many referrals from the same IP address in a short time")

        # 7. Max referrals per payment check is enforced in payment webhook handler
        # by checking ReferralStatus.QUALIFIED count per referrer per payment

    async def ensure_referral_code(self, student: Student) -> str:
        """Ensure student has a referral code, generate if missing."""
        if student.referral_code:
            return student.referral_code

        code = await self.generate_unique_code()
        student.referral_code = code
        await self._db.commit()
        await self._db.refresh(student)
        return code

    async def get_referral_link(self, student: Student, base_url: str | None = None) -> str:
        """Get the full referral link for a student."""
        code = await self.ensure_referral_code(student)
        base = base_url or "https://spetser.ai"
        return f"{base}/r/{code}"

    async def validate_referral_code(self, code: str) -> Student | None:
        """Validate a referral code and return the referrer if valid."""
        if not code or not code.startswith(self.PREFIX + "-"):
            return None

        result = await self._db.execute(
            select(Student).where(Student.referral_code == code)
        )
        referrer = result.scalar_one_or_none()
        return referrer

    async def get_referral_stats(self, student: Student) -> dict:
        """Get referral statistics for a student."""
        # Count referrals by status
        total_result = await self._db.execute(
            select(Referral).where(Referral.referrer_user_id == student.id)
        )
        total = len(total_result.scalars().all())

        qualified_result = await self._db.execute(
            select(Referral).where(
                Referral.referrer_user_id == student.id,
                Referral.status == ReferralStatus.QUALIFIED
            )
        )
        qualified = len(qualified_result.scalars().all())

        rewarded_result = await self._db.execute(
            select(Referral).where(
                Referral.referrer_user_id == student.id,
                Referral.status == ReferralStatus.REWARDED
            )
        )
        rewarded = len(rewarded_result.scalars().all())

        # Total earnings from rewards
        earnings_result = await self._db.execute(
            select(RewardTransaction.amount).where(
                RewardTransaction.user_id == student.id,
                RewardTransaction.status == RewardStatus.PAID
            )
        )
        total_earnings = sum(row[0] for row in earnings_result.all()) if earnings_result else Decimal("0")

        code = await self.ensure_referral_code(student)
        return {
            "total_referrals": total,
            "qualified_referrals": qualified,
            "rewarded_referrals": rewarded,
            "total_earnings_usd": str(total_earnings),
            "referral_link": await self.get_referral_link(student),
            "referral_code": code,
        }

    # ── Reward logic (Lesson 7.5) ────────────────────────────────────────────

    def _commission_amount(self, paid_usd: Decimal) -> Decimal:
        """Referrer's commission for a given payment amount (rounded to cents)."""
        percent = get_settings().referral_reward_percent
        return (paid_usd * percent / Decimal("100")).quantize(Decimal("0.01"))

    async def on_invoice_paid(self, invoice: "PaymentInvoice") -> RewardTransaction | None:
        """Called when a referred user's invoice turns PAID.

        Idempotent (keyed on referral_id): a second call for the same
        referral returns the existing reward without creating a duplicate.
        """
        referral = (await self._db.execute(
            select(Referral).where(Referral.referred_user_id == invoice.user_id)
        )).scalar_one_or_none()
        if referral is None:
            return None  # payer was not referred by anyone
        if referral.status == ReferralStatus.REVOKED:
            return None

        # Exactly-once: one reward per referral (Lesson 7.5 / 6.x webhook replay).
        existing = (await self._db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id)
        )).scalar_one_or_none()
        if existing is not None:
            return existing

        now = datetime.now(timezone.utc)
        holding = timedelta(days=get_settings().referral_reward_holding_days)
        reward = RewardTransaction(
            id=uuid.uuid4(),
            user_id=referral.referrer_user_id,
            referral_id=referral.id,
            amount=self._commission_amount(invoice.amount_usd),
            currency="USD_CREDIT",
            type=RewardType.SUBSCRIPTION_COMMISSION,
            status=RewardStatus.PENDING,
            scheduled_release_at=now + holding,
            reference_invoice_id=invoice.id,
        )
        referral.status = ReferralStatus.QUALIFIED
        referral.qualified_at = now
        self._db.add(reward)
        await self._db.commit()
        await self._db.refresh(reward)
        return reward

    async def release_due_rewards(self) -> list[RewardTransaction]:
        """Release rewards whose holding period has elapsed.

        Each released reward credits the referrer (exactly-once via ledger
        idempotency_key) and flips the referral to REWARDED.
        """
        from app.services.credit_service import CreditService

        now = datetime.now(timezone.utc)
        due = (await self._db.execute(
            select(RewardTransaction).where(
                RewardTransaction.status == RewardStatus.PENDING,
                RewardTransaction.scheduled_release_at <= now,
            )
        )).scalars().all()

        released: list[RewardTransaction] = []
        for reward in due:
            if await self._release_one(reward, now):
                released.append(reward)
        await self._db.commit()
        return released

    async def _release_one(self, reward: RewardTransaction,
                           now: datetime) -> bool:
        """Credit the referrer for one reward. Returns False if skipped."""
        from app.services.credit_service import CreditService

        if reward.referral_id is not None:
            referral = (await self._db.execute(
                select(Referral).where(Referral.id == reward.referral_id)
            )).scalar_one_or_none()
            if referral is not None and referral.status == ReferralStatus.REVOKED:
                reward.status = RewardStatus.REVOKED
                return False

        referrer = (await self._db.execute(
            select(Student).where(Student.id == reward.user_id)
        )).scalar_one()
        credits = CreditService(self._db, referrer)
        await credits.add_credits(
            reward.amount,
            entry_type="referral_reward",
            description=f"reward:{reward.id}",
            reference_type="referral", reference_id=reward.referral_id,
            idempotency_key=f"ref-reward-{reward.id}",
        )
        reward.status = RewardStatus.PAID
        if reward.referral_id is not None:
            referral = (await self._db.execute(
                select(Referral).where(Referral.id == reward.referral_id)
            )).scalar_one_or_none()
            if referral is not None:
                referral.status = ReferralStatus.REWARDED
                referral.rewarded_at = now
        return True

    async def force_release_referral(self, referral_id: uuid.UUID) -> RewardTransaction:
        """Admin override (Lesson 7.6): release a held reward immediately."""
        referral = (await self._db.execute(
            select(Referral).where(Referral.id == referral_id)
        )).scalar_one_or_none()
        if referral is None:
            raise NotFoundError("الإحالة غير موجودة.")
        if referral.status == ReferralStatus.REVOKED:
            raise ValidationError("لا يمكن إطلاق مكافأة إحالة ملغاة.")

        reward = (await self._db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id,
                RewardTransaction.status == RewardStatus.PENDING,
            )
        )).scalar_one_or_none()
        if reward is None:
            raise ConflictError("لا توجد مكافأة قيد الانتظار لهذه الإحالة.")

        await self._release_one(reward, datetime.now(timezone.utc))
        await self._db.commit()
        await self._db.refresh(reward)
        return reward

    async def revoke_referral(self, referral_id: uuid.UUID) -> Referral:
        """Admin action (Lesson 7.6): revoke a referral and any unpaid reward."""
        referral = (await self._db.execute(
            select(Referral).where(Referral.id == referral_id)
        )).scalar_one_or_none()
        if referral is None:
            raise NotFoundError("الإحالة غير موجودة.")
        referral.status = ReferralStatus.REVOKED
        rewards = (await self._db.execute(
            select(RewardTransaction).where(
                RewardTransaction.referral_id == referral.id,
                RewardTransaction.status == RewardStatus.PENDING,
            )
        )).scalars().all()
        for reward in rewards:
            reward.status = RewardStatus.REVOKED
        await self._db.commit()
        await self._db.refresh(referral)
        return referral