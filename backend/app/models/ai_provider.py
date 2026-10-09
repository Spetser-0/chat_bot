"""
app/models/ai_provider.py
──────────────────────────
AI provider configuration for multi-provider LLM routing.
Stores encrypted API keys and provider settings.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.skill import Skill


class AIProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    AI provider configuration (e.g., Anthropic, Google, OpenAI).
    
    Security Note: api_key_encrypted must be encrypted using Fernet encryption
    before storing. Never store plaintext API keys in the database.
    """

    __tablename__ = "ai_providers"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Encrypted API key (use Fernet encryption, never store plaintext)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Load balancing and failover
    priority_weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    
    # Timeout and retry configuration
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    
    # Cost tracking (per 1000 tokens)
    cost_input_per_1k: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6), nullable=False, default=Decimal("0.001")
    )
    cost_output_per_1k: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6), nullable=False, default=Decimal("0.002")
    )
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    
    # Additional configuration (model-specific parameters)
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    skills_as_preferred: Mapped[list[Skill]] = relationship(
        "Skill",
        foreign_keys="Skill.preferred_provider_id",
        back_populates="preferred_provider",
        lazy="select",
    )
    skills_as_fallback: Mapped[list[Skill]] = relationship(
        "Skill",
        foreign_keys="Skill.fallback_provider_id",
        back_populates="fallback_provider",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<AIProvider id={self.id} slug={self.slug} active={self.is_active}>"
