"""
app/models/reward_transaction.py
─────────────────────────────────
Referral reward transactions.
Tracks reward distribution for successful referrals.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payment_invoice import PaymentInvoice
    from app.models.referral import Referral
    from app.models.student import Student


class RewardType(str):
    """Reward type constants."""
    SIGNUP_BONUS = "signup_bonus"
    SUBSCRIPTION_COMMISSION = "subscription_commission"
    MANUAL_BONUS = "manual_bonus"


class RewardStatus(str):
    """Reward status constants."""
    PENDING = "pending"
    PAYABLE = "payable"
    PAID = "paid"
    REVOKED = "revoked"


class RewardTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Referral reward transaction.
    
    Tracks rewards earned through referrals with holding periods.
    """

    __tablename__ = "reward_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referral_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("referrals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # Reward details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="USD_CREDIT"
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Status and release
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RewardStatus.PENDING, index=True
    )
    scheduled_release_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    
    # Reference to triggering payment
    reference_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_invoices.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped[Student] = relationship(
        "Student", foreign_keys=[user_id], lazy="select"
    )
    referral: Mapped[Referral | None] = relationship(
        "Referral", back_populates="rewards"
    )
    reference_invoice: Mapped[PaymentInvoice | None] = relationship(
        "PaymentInvoice", foreign_keys=[reference_invoice_id], lazy="select"
    )

    def __repr__(self) -> str:
        return f"<RewardTransaction id={self.id} user_id={self.user_id} status={self.status}>"
