"""
app/services/admin/provider_service.py
────────────────────────────────────────
Provider management service for Developer Dashboard.
CRUD operations for AI providers with secure key handling.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.provider import ModelProvider

if TYPE_CHECKING:
    from app.services.providers.base import AIProvider


class ProviderService:
    """Service for managing AI providers."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_providers(self) -> list[ModelProvider]:
        """List all providers."""
        result = await self._db.execute(select(ModelProvider).order_by(ModelProvider.display_name))
        return list(result.scalars().all())

    async def get_provider(self, provider_id: uuid.UUID) -> ModelProvider:
        """Get a provider by ID."""
        result = await self._db.execute(select(ModelProvider).where(ModelProvider.id == provider_id))
        provider = result.scalar_one_or_none()
        if provider is None:
            raise NotFoundError("Provider not found")
        return provider

    async def get_provider_by_key(self, provider_key: str) -> ModelProvider:
        """Get a provider by key."""
        result = await self._db.execute(select(ModelProvider).where(ModelProvider.provider_key == provider_key))
        provider = result.scalar_one_or_none()
        if provider is None:
            raise NotFoundError("Provider not found")
        return provider

    async def create_provider(
        self,
        *,
        provider_key: str,
        display_name: str,
        api_key: str | None = None,
        enabled: bool = True,
    ) -> ModelProvider:
        """Create a new provider."""
        # Check if key already exists
        existing = await self._db.execute(select(ModelProvider).where(ModelProvider.provider_key == provider_key))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Provider with key '{provider_key}' already exists")

        provider = ModelProvider(
            id=uuid.uuid4(),
            provider_key=provider_key,
            display_name=display_name,
            enabled=enabled,
            secret_reference=api_key,  # In production, this should be encrypted/stored in secret manager
        )
        self._db.add(provider)
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def update_provider(
        self,
        provider_id: uuid.UUID,
        *,
        display_name: str | None = None,
        api_key: str | None = None,
        enabled: bool | None = None,
    ) -> ModelProvider:
        """Update a provider."""
        provider = await self.get_provider(provider_id)

        if display_name is not None:
            provider.display_name = display_name
        if api_key is not None:
            provider.secret_reference = api_key
        if enabled is not None:
            provider.enabled = enabled

        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def delete_provider(self, provider_id: uuid.UUID) -> None:
        """Delete a provider."""
        provider = await self.get_provider(provider_id)
        await self._db.delete(provider)
        await self._db.commit()

    async def test_provider(self, provider_id: uuid.UUID) -> bool:
        """Test provider connectivity."""
        provider = await self.get_provider(provider_id)

        # Get provider adapter from registry
        from app.services.providers.registry import get_provider as get_provider_adapter

        try:
            adapter = get_provider_adapter(provider.provider_key)
            return await adapter.health_check()
        except Exception:
            return False

    async def rotate_key(self, provider_id: uuid.UUID, new_api_key: str) -> ModelProvider:
        """Rotate provider API key."""
        provider = await self.get_provider(provider_id)
        provider.secret_reference = new_api_key  # In production, encrypt and store in secret manager
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    def get_provider_instance(self, provider_key: str) -> "AIProvider":
        """Get provider adapter instance."""
        from app.services.providers.registry import get_provider
        return get_provider(provider_key)