"""
app/models/skill.py
────────────────────
AI skill/personality configuration.
Each skill defines a specialized AI behavior with custom prompts and settings.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ai_provider import AIProvider
    from app.models.skill_tool import SkillTool
    from app.models.student import Student


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    AI skill configuration (e.g., math-tutor, essay-helper).
    
    Defines specialized AI behavior through system prompts, model preferences,
    and tool access permissions.
    """

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Model configuration
    temperature: Mapped[Decimal] = mapped_column(
        Numeric(precision=3, scale=2), nullable=False, default=Decimal("0.7")
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4096, server_default="4096"
    )
    
    # Provider preferences
    preferred_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_providers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fallback_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_providers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Access control
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    is_premium: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    
    # Cost management
    cost_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(precision=4, scale=2), nullable=False, default=Decimal("1.0")
    )
    
    # Versioning
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    
    # Creator tracking
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    preferred_provider: Mapped[AIProvider | None] = relationship(
        "AIProvider",
        foreign_keys=[preferred_provider_id],
        back_populates="skills_as_preferred",
        lazy="select",
    )
    fallback_provider: Mapped[AIProvider | None] = relationship(
        "AIProvider",
        foreign_keys=[fallback_provider_id],
        back_populates="skills_as_fallback",
        lazy="select",
    )
    tools: Mapped[list[SkillTool]] = relationship(
        "SkillTool",
        back_populates="skill",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    created_by: Mapped[Student | None] = relationship(
        "Student",
        foreign_keys=[created_by_user_id],
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id} slug={self.slug} public={self.is_public}>"
