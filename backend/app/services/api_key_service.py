"""
app/services/api_key_service.py
───────────────────────────────
API Key management service for developer panel.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.api_key import APIKey


def _to_uuid(val: str | uuid.UUID) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        raise NotFoundError("API key not found.")


class APIKeyService:
    """Manages API key lifecycle for developer panel."""

    KEY_PREFIX = "sk-spetser-"

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def generate_key(self) -> str:
        """Generate a secure, random API key."""
        random_part = secrets.token_urlsafe(32)
        return f"{self.KEY_PREFIX}{random_part}"

    async def create_key(
        self,
        db: AsyncSession,
        name: str,
        created_by: str | uuid.UUID,
        system_prompt: str | None = None,
        max_credits_per_day: int | None = None,
        allowed_skills: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.
        Returns the APIKey model and the plain key string (shown only once).
        """
        plain_key = self.generate_key()

        api_key = APIKey(
            name=name,
            key_hash=self._hash_key(plain_key),
            key_prefix=plain_key[: len(self.KEY_PREFIX) + 4],
            system_prompt=system_prompt,
            max_credits_per_day=max_credits_per_day,
            allowed_skills=allowed_skills,  # stored as JSON/JSONB array
            expires_at=expires_at,
            created_by=created_by if isinstance(created_by, uuid.UUID) else uuid.UUID(str(created_by)),
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        return api_key, plain_key

    async def verify_key(self, db: AsyncSession, plain_key: str) -> APIKey | None:
        """Verify an API key and update usage statistics."""
        key_hash = self._hash_key(plain_key)
        result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()

        if not api_key or not api_key.is_active:
            return None

        if api_key.expires_at:
            expires_at = api_key.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return None

        # Update usage metrics
        api_key.last_used_at = datetime.now(timezone.utc)
        api_key.total_requests += 1
        await db.commit()
        await db.refresh(api_key)

        return api_key

    async def update_key(
        self,
        db: AsyncSession,
        key_id: str,
        **updates,
    ) -> APIKey:
        """Update API key settings."""
        result = await db.execute(select(APIKey).where(APIKey.id == _to_uuid(key_id)))
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key not found.")

        allowed_fields = {
            "name",
            "system_prompt",
            "max_credits_per_day",
            "allowed_skills",
            "is_active",
            "expires_at",
        }
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(api_key, field, value)

        await db.commit()
        await db.refresh(api_key)
        return api_key

    async def delete_key(self, db: AsyncSession, key_id: str) -> None:
        """Delete an API key."""
        result = await db.execute(select(APIKey).where(APIKey.id == _to_uuid(key_id)))
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key not found.")

        await db.delete(api_key)
        await db.commit()

    async def regenerate_key(self, db: AsyncSession, key_id: str) -> tuple[APIKey, str]:
        """Regenerate key value, invalidating previous key."""
        result = await db.execute(select(APIKey).where(APIKey.id == _to_uuid(key_id)))
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key not found.")

        plain_key = self.generate_key()
        api_key.key_hash = self._hash_key(plain_key)
        api_key.key_prefix = plain_key[: len(self.KEY_PREFIX) + 4]
        await db.commit()
        await db.refresh(api_key)

        return api_key, plain_key


api_key_service = APIKeyService()
