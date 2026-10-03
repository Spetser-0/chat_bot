"""app/models/provider.py — AI provider registry."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ModelProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_providers"

    provider_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )  # e.g. "anthropic", "google_gemini"
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Reference to secret manager or encrypted value — NOT the raw key
    secret_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    health_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    configurations = relationship(
        "ModelConfiguration", back_populates="provider", lazy="select"
    )


"""app/models/model_configuration.py — Model/tier configuration per provider."""
