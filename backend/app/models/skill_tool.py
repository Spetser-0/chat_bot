"""
app/models/skill_tool.py
─────────────────────────
Tool bindings for AI skills.
Defines which tools (web_search, calculator, etc.) a skill can use.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.skill import Skill


class SkillTool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Tool binding for a skill.
    
    Defines which tools a skill can call and their configuration.
    """

    __tablename__ = "skill_tools"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Relationships
    skill: Mapped[Skill] = relationship("Skill", back_populates="tools")

    def __repr__(self) -> str:
        return f"<SkillTool skill_id={self.skill_id} tool={self.tool_name}>"
