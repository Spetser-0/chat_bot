"""
app/models/student.py
──────────────────────
Authenticated platform user (student or developer).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.credit_ledger import CreditLedger
    from app.models.request import Request


class StudentRole(str):
    STUDENT = "student"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class StudentStatus(str):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"

    external_auth_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # bcrypt hash — never plain text
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="student", index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Incrementing this value revokes every previously issued session token.
    session_version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    # Use Decimal for monetary values — never FLOAT
    credit_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=4), nullable=False, default=Decimal("100.0")
    )

    # ━━━ Phase 1: Referral System Fields ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    referral_code: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    referred_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ━━━ Phase 1: Premium Subscription Fields ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    is_premium: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    premium_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ━━━ Phase 1: Security & Account Protection ━━━━━━━━━━━━━━━━━━━━━━━━━
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # ━━━ Relationships ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    requests: Mapped[list[Request]] = relationship(
        "Request", back_populates="student", lazy="select"
    )
    credit_ledger_entries: Mapped[list[CreditLedger]] = relationship(
        "CreditLedger", back_populates="student", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id} email={self.email} role={self.role}>"
