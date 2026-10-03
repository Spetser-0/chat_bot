"""app/models/source_record.py — Citation and source verification record."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class VerificationStatus:
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    BROKEN = "broken"
    DISPUTED = "disputed"


class SourceRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "source_records"

    deliverable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deliverables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=VerificationStatus.UNVERIFIED
    )
    source_metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    deliverable = relationship("Deliverable", back_populates="sources")
