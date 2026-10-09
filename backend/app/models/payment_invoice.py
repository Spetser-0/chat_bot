"""
app/models/payment_invoice.py
───────────────────────────────
Cryptocurrency payment invoices.
Tracks payment status and webhook data for crypto payments.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.student import Student


class PaymentStatus(str):
    """Payment status constants."""
    PENDING = "pending"
    CONFIRMING = "confirming"
    PAID = "paid"
    EXPIRED = "expired"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentInvoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Cryptocurrency payment invoice.
    
    Tracks crypto payments from creation through confirmation.
    """

    __tablename__ = "payment_invoices"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Provider information
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_invoice_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    
    # Amount details
    amount_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    crypto_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=8), nullable=True
    )
    
    # Payment details
    crypto_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Webhook data
    webhook_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Relationships
    user: Mapped[Student] = relationship("Student", lazy="select")

    def __repr__(self) -> str:
        return f"<PaymentInvoice id={self.id} user_id={self.user_id} status={self.status}>"
