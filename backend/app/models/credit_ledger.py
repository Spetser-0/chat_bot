"""app/models/credit_ledger.py — Append-only credit usage ledger."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import String, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class LedgerEntryType:
    CHARGE = "charge"
    RESERVATION = "reservation"
    RELEASE = "release"
    REFUND = "refund"
    GRANT = "grant"


class CreditLedger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "credit_ledger"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Use NUMERIC for monetary values — never FLOAT
    computed_usd_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )
    pricing_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    credits_charged: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), nullable=False, default=Decimal("0")
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Idempotency key prevents double-charging on retry
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    student = relationship("Student", back_populates="credit_ledger_entries")
