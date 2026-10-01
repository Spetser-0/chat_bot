"""
app/services/admin/model_config_service.py
────────────────────────────────────────────
Model Configuration management service for Developer Dashboard.
CRUD operations for model configurations with tier assignment.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.model_configuration import ModelConfiguration

if TYPE_CHECKING:
    from app.services.providers.base import AIProvider


class ModelConfigService:
    """Service for managing model configurations."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_configs(self) -> list[ModelConfiguration]:
        """List all model configurations."""
        result = await self._db.execute(
            select(ModelConfiguration).order_by(ModelConfiguration.tier, ModelConfiguration.model_name)
        )
        return list(result.scalars().all())

    async def get_config(self, config_id: uuid.UUID) -> ModelConfiguration:
        """Get a model configuration by ID."""
        result = await self._db.execute(select(ModelConfiguration).where(ModelConfiguration.id == config_id))
        config = result.scalar_one_or_none()
        if config is None:
            raise NotFoundError("Model configuration not found")
        return config

    async def get_configs_by_tier(self, tier: str) -> list[ModelConfiguration]:
        """Get all configurations for a specific tier."""
        result = await self._db.execute(
            select(ModelConfiguration).where(
                ModelConfiguration.tier == tier,
                ModelConfiguration.enabled == True,
            )
        )
        return list(result.scalars().all())

    async def get_configs_by_provider(self, provider_id: uuid.UUID) -> list[ModelConfiguration]:
        """Get all configurations for a provider."""
        result = await self._db.execute(
            select(ModelConfiguration).where(ModelConfiguration.provider_id == provider_id)
        )
        return list(result.scalars().all())

    async def create_config(
        self,
        *,
        provider_id: uuid.UUID,
        model_name: str,
        tier: str,
        capabilities: list[str] | None = None,
        input_price_per_1k: Decimal,
        output_price_per_1k: Decimal,
        max_tokens: int | None = None,
        context_window: int | None = None,
        enabled: bool = True,
        fallback_priority: int = 100,
    ) -> ModelConfiguration:
        """Create a new model configuration."""
        # Verify provider exists
        from app.models.provider import ModelProvider
        provider_result = await self._db.execute(select(ModelProvider).where(ModelProvider.id == provider_id))
        if provider_result.scalar_one_or_none() is None:
            raise NotFoundError("Provider not found")

        config = ModelConfiguration(
            id=uuid.uuid4(),
            provider_id=provider_id,
            model_name=model_name,
            tier=tier,
            capabilities_json=capabilities,
            input_price_per_1k_tokens=input_price_per_1k,
            output_price_per_1k_tokens=output_price_per_1k,
            max_tokens=max_tokens,
            context_window=context_window,
            enabled=enabled,
            fallback_priority=fallback_priority,
        )
        self._db.add(config)
        await self._db.commit()
        await self._db.refresh(config)
        return config

    async def update_config(
        self,
        config_id: uuid.UUID,
        *,
        model_name: str | None = None,
        tier: str | None = None,
        capabilities: list[str] | None = None,
        input_price_per_1k: Decimal | None = None,
        output_price_per_1k: Decimal | None = None,
        max_tokens: int | None = None,
        context_window: int | None = None,
        enabled: bool | None = None,
        fallback_priority: int | None = None,
    ) -> ModelConfiguration:
        """Update a model configuration."""
        config = await self.get_config(config_id)

        if model_name is not None:
            config.model_name = model_name
        if tier is not None:
            config.tier = tier
        if capabilities is not None:
            config.capabilities_json = capabilities
        if input_price_per_1k is not None:
            config.input_price_per_1k_tokens = input_price_per_1k
        if output_price_per_1k is not None:
            config.output_price_per_1k_tokens = output_price_per_1k
        if max_tokens is not None:
            config.max_tokens = max_tokens
        if context_window is not None:
            config.context_window = context_window
        if enabled is not None:
            config.enabled = enabled
        if fallback_priority is not None:
            config.fallback_priority = fallback_priority

        await self._db.commit()
        await self._db.refresh(config)
        return config

    async def delete_config(self, config_id: uuid.UUID) -> None:
        """Delete a model configuration."""
        config = await self.get_config(config_id)
        await self._db.delete(config)
        await self._db.commit()

    async def enable_config(self, config_id: uuid.UUID, enabled: bool) -> ModelConfiguration:
        """Enable or disable a model configuration."""
        config = await self.get_config(config_id)
        config.enabled = enabled
        await self._db.commit()
        await self._db.refresh(config)
        return config