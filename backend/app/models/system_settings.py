"""
app/models/system_settings.py
─────────────────────────────
Global system settings model for default credits and limits.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SystemSettings(Base):
    """Global system settings singleton."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_new_user_credits: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
    daily_free_credits: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
    credits_per_message: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SystemSettings id={self.id} default_credits={self.default_new_user_credits}>"
