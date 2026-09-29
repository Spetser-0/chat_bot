"""
app/models/request.py
──────────────────────
Tracks every student AI request with its full lifecycle.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.deliverable import Deliverable
    from app.models.prompt_version import PromptVersion


class RequestStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING = "generating"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ALL = [PENDING, PROCESSING, GENERATING, VALIDATING, READY, FAILED, CANCELLED]


class Request(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requests"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="default")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=RequestStatus.PENDING, index=True
    )
    # SHA-256 of canonical request payload JSON
    request_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Client-supplied idempotency key (scoped to student)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Resolved provider/model from routing
    resolved_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Safe error code (never raw exception or prompt text)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Human-facing title for history display
    display_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    student: Mapped["Student"] = relationship("Student", back_populates="requests")
    deliverables: Mapped[list["Deliverable"]] = relationship(
        "Deliverable", back_populates="request", lazy="select"
    )
    prompt_version: Mapped["PromptVersion | None"] = relationship(
        "PromptVersion", lazy="select", foreign_keys=[prompt_version_id]
    )

    def __repr__(self) -> str:
        return f"<Request id={self.id} feature={self.feature} status={self.status}>"
