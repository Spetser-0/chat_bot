"""app/models/deliverable.py — Generated file deliverable record."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.request import Request
    from app.models.source_record import SourceRecord


class DeliverableStatus:
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class Deliverable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deliverables"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pptx | pdf | json
    storage_object_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    renderer_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeliverableStatus.PENDING
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    request: Mapped[Request] = relationship("Request", back_populates="deliverables")
    sources: Mapped[list[SourceRecord]] = relationship(
        "SourceRecord", back_populates="deliverable", lazy="select"
    )
