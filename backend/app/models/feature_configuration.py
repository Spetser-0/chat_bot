"""app/models/feature_configuration.py — Per-feature platform configuration."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FeatureConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feature_configurations"

    feature_key: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # chat | presentation | research | question_solver
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="default")
    active_prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    response_schema_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
