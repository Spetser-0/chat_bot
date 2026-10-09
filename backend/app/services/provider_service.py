"""
app/services/provider_service.py
─────────────────────────────────
Provider CRUD service for the multi-provider AI router.

Distinction from app/services/admin/provider_service.py:
  That legacy service manages the OLD `ModelProvider` table (plaintext
  secret_reference). THIS service manages the NEW `AIProvider` table
  whose API keys are Fernet-encrypted at rest (Phase 3 router).

Security:
- API keys are written ONLY via encrypt_secret(); read back with
  decrypt_secret() at call time. Plaintext keys never leave process
  memory and are never logged (see app/core/logging.py redaction).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import decrypt_secret, encrypt_secret, mask_api_key
from app.models.ai_provider import AIProvider

# Capabilities this router currently supports. Extend when adding skills.
SUPPORTED_CAPABILITIES = frozenset({"chat", "streaming"})


class ProviderService:
    """CRUD + pre-call validation for AIProvider rows (encrypted keys)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Reads ──────────────────────────────────────────────────────────
    async def list_all(self) -> list[AIProvider]:
        """Every provider (active + inactive) for the admin dashboard."""
        result = await self._db.execute(
            select(AIProvider).order_by(AIProvider.priority_weight.desc(),
                                        AIProvider.name)
        )
        return list(result.scalars().all())

    async def list_active(self) -> list[AIProvider]:
        """All active providers ordered by priority_weight (highest first)."""
        result = await self._db.execute(
            select(AIProvider)
            .where(AIProvider.is_active.is_(True))
            .order_by(AIProvider.priority_weight.desc(), AIProvider.name)
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> AIProvider:
        """Fetch one provider by unique slug or raise NotFoundError."""
        result = await self._db.execute(
            select(AIProvider).where(AIProvider.slug == slug)
        )
        provider = result.scalar_one_or_none()
        if provider is None:
            raise NotFoundError(f"Provider '{slug}' not found")
        return provider

    # ── Writes ─────────────────────────────────────────────────────────
    async def create(self, *, data: dict[str, Any]) -> AIProvider:
        """Insert new provider; encrypt api_key. Conflict on slug collision."""
        slug = data.get("slug")
        if not slug:
            raise ValidationError("slug is required")
        existing = await self._db.execute(
            select(AIProvider.id).where(AIProvider.slug == slug)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Provider with slug '{slug}' already exists")

        plaintext_key = data.pop("api_key", None)
        if not plaintext_key:
            raise ValidationError("api_key is required")

        provider = AIProvider(
            id=uuid.uuid4(),
            api_key_encrypted=encrypt_secret(plaintext_key),
            **data,
        )
        self._db.add(provider)
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def update(self, slug: str, *, data: dict[str, Any]) -> AIProvider:
        """Update fields; re-encrypt api_key when present."""
        provider = await self.get_by_slug(slug)
        payload = dict(data)  # don't mutate caller's dict
        plaintext_key = payload.pop("api_key", None)
        if plaintext_key is not None:
            provider.api_key_encrypted = encrypt_secret(plaintext_key)
        for field, value in payload.items():
            setattr(provider, field, value)
        await self._db.commit()
        await self._db.refresh(provider)
        return provider

    async def delete(self, slug: str) -> None:
        """Permanently remove a provider row."""
        provider = await self.get_by_slug(slug)
        await self._db.delete(provider)
        await self._db.commit()

    # ── Router-facing helpers ──────────────────────────────────────────
    async def decrypted_key(self, provider: AIProvider) -> str:
        """Return plaintext API key for a live call. Never log this value."""
        settings = get_settings()
        if not settings.llm_master_encryption_key:
            raise ValidationError("LLM_MASTER_ENCRYPTION_KEY not configured")
        return decrypt_secret(provider.api_key_encrypted)

    def masked_key_preview(self, provider: AIProvider) -> str:
        """Safe 'sk-***abcd' preview for admin dashboards."""
        plaintext = decrypt_secret(provider.api_key_encrypted)
        return mask_api_key(plaintext)

    async def validate_for_call(
        self, provider: AIProvider, capability: str = "chat"
    ) -> None:
        """Fail fast before a routing attempt: active + decryptable key."""
        if capability not in SUPPORTED_CAPABILITIES:
            raise ValidationError(f"Unsupported capability '{capability}'")
        if not provider.is_active:
            raise ConflictError(f"Provider '{provider.slug}' is inactive")
        # Forces decryption now so misconfigured keys fail at selection
        # time, not mid-stream. Value discarded immediately.
        await self.decrypted_key(provider)
