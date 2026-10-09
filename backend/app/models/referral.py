"""
app/models/referral.py
───────────────────────
User referral tracking.
Tracks referral relationships and qualification status.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.reward_transaction import RewardTransaction
    from app.models.student import Student


class ReferralStatus(str):
    """Referral status constants."""
    PENDING = "pending"
    QUALIFIED = "qualified"
    REWARDED = "rewarded"
    REVOKED = "revoked"


class Referral(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    User referral tracking.
    
    Records when a user refers another user and tracks reward status.
    """

    __tablename__ = "referrals"

    referrer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referred_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One user can only be referred once
        index=True,
    )
    referral_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Attribution context (for fraud detection)
    landing_page_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReferralStatus.PENDING, index=True
    )
    qualified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rewarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    referrer: Mapped[Student] = relationship(
        "Student",
        foreign_keys=[referrer_user_id],
        lazy="select",
    )
    referred_user: Mapped[Student] = relationship(
        "Student",
        foreign_keys=[referred_user_id],
        lazy="select",
    )
    rewards: Mapped[list[RewardTransaction]] = relationship(
        "RewardTransaction",
        back_populates="referral",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Referral id={self.id} status={self.status} code={self.referral_code}>"
