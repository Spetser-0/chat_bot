"""app/models/routing_rule.py — Feature+tier → primary/fallback model routing."""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RoutingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "routing_rules"

    feature_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    primary_model_configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_configurations.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Ordered list of fallback model_configuration IDs stored as JSON to support SQLite
    fallback_model_configuration_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
