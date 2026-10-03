"""app/models/model_configuration.py — Specific model + tier config."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ModelConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_configurations"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # JSON list: ["json", "vision", "reasoning", "streaming"]
    capabilities_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    input_price_per_1k_tokens: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal(0)
    )
    output_price_per_1k_tokens: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal(0)
    )
    pricing_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fallback_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    provider = relationship("ModelProvider", back_populates="configurations")
