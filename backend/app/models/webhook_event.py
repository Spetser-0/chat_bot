"""
app/models/webhook_event.py
────────────────────────────
Payment webhook event tracking.
Prevents duplicate webhook processing through deduplication.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Payment webhook event log.
    
    Stores raw webhook data and prevents duplicate processing.
    """

    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Webhook data
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signature: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Processing status
    processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WebhookEvent id={self.id} provider={self.provider} processed={self.processed}>"
