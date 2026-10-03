"""
app/services/admin/prompt_version_service.py
──────────────────────────────────────────────────
Prompt Version management service for Developer Dashboard.
CRUD operations for prompt versions with versioning and activation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.prompt_version import PromptStatus, PromptVersion

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PromptVersionService:
    """Service for managing prompt versions with versioning."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_prompts(self, feature_key: str | None = None) -> list[dict]:
        """List all prompt versions, optionally filtered by feature."""
        query = select(PromptVersion).order_by(PromptVersion.feature_key, PromptVersion.created_at.desc())
        if feature_key:
            query = query.where(PromptVersion.feature_key == feature_key)
        result = await self._db.execute(query)
        prompts = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "feature_key": p.feature_key,
                "version": p.version,
                "content": p.content,
                "status": p.status,
                "change_note": p.change_note,
                "created_by": str(p.created_by) if p.created_by else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "activated_at": p.activated_at.isoformat() if p.activated_at else None,
            }
            for p in prompts
        ]

    async def get_prompt(self, prompt_id: uuid.UUID) -> dict:
        """Get a prompt version by ID."""
        result = await self._db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError("Prompt version not found")

        return {
            "id": str(prompt.id),
            "feature_key": prompt.feature_key,
            "version": prompt.version,
            "content": prompt.content,
            "status": prompt.status,
            "change_note": prompt.change_note,
            "created_by": str(prompt.created_by) if prompt.created_by else None,
            "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
            "activated_at": prompt.activated_at.isoformat() if prompt.activated_at else None,
        }

    async def create_prompt(
        self,
        *,
        feature_key: str,
        version: str,
        content: str,
        change_note: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> dict:
        """Create a new prompt version."""
        # Check if version already exists for this feature
        existing = await self._db.execute(
            select(PromptVersion).where(
                PromptVersion.feature_key == feature_key,
                PromptVersion.version == version,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Prompt version '{version}' already exists for feature '{feature_key}'")

        prompt = PromptVersion(
            id=uuid.uuid4(),
            feature_key=feature_key,
            version=version,
            content=content,
            status=PromptStatus.DRAFT,
            change_note=change_note,
            created_by=created_by,
        )
        self._db.add(prompt)
        await self._db.commit()
        await self._db.refresh(prompt)

        return await self.get_prompt(prompt.id)

    async def update_prompt(
        self,
        prompt_id: uuid.UUID,
        *,
        content: str | None = None,
        change_note: str | None = None,
    ) -> dict:
        """Update a prompt version (only if DRAFT)."""
        result = await self._db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError("Prompt version not found")

        if prompt.status != PromptStatus.DRAFT:
            raise ConflictError("Can only update DRAFT prompts")

        if content is not None:
            prompt.content = content
        if change_note is not None:
            prompt.change_note = change_note

        await self._db.commit()
        await self._db.refresh(prompt)

        return await self.get_prompt(prompt_id)

    async def activate_prompt(self, prompt_id: uuid.UUID, activated_by: uuid.UUID) -> dict:
        """Activate a prompt version, archiving the currently active one."""
        result = await self._db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError("Prompt version not found")

        if prompt.status == PromptStatus.ACTIVE:
            raise ConflictError("Prompt is already active")

        # Archive currently active prompt for this feature
        active_result = await self._db.execute(
            select(PromptVersion).where(
                PromptVersion.feature_key == prompt.feature_key,
                PromptVersion.status == PromptStatus.ACTIVE,
            )
        )
        active_prompt = active_result.scalar_one_or_none()
        if active_prompt:
            active_prompt.status = PromptStatus.ARCHIVED

        # Activate the new prompt
        prompt.status = PromptStatus.ACTIVE
        prompt.activated_at = datetime.now(UTC)
        prompt.activated_at = datetime.now(UTC)

        await self._db.commit()
        await self._db.refresh(prompt)

        return await self.get_prompt(prompt_id)

    async def archive_prompt(self, prompt_id: uuid.UUID) -> dict:
        """Archive a prompt version."""
        result = await self._db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError("Prompt version not found")

        if prompt.status == PromptStatus.ACTIVE:
            raise ConflictError("Cannot archive active prompt. Activate another first.")

        prompt.status = PromptStatus.ARCHIVED
        await self._db.commit()
        await self._db.refresh(prompt)

        return await self.get_prompt(prompt_id)

    async def duplicate_prompt(self, prompt_id: uuid.UUID, new_version: str, change_note: str | None = None) -> dict:
        """Duplicate a prompt version with a new version number."""
        result = await self._db.execute(select(PromptVersion).where(PromptVersion.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise NotFoundError("Prompt version not found")

        # Check if new version exists
        existing = await self._db.execute(
            select(PromptVersion).where(
                PromptVersion.feature_key == prompt.feature_key,
                PromptVersion.version == new_version,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Version '{new_version}' already exists")

        new_prompt = PromptVersion(
            id=uuid.uuid4(),
            feature_key=prompt.feature_key,
            version=new_version,
            content=prompt.content,
            status=PromptStatus.DRAFT,
            change_note=change_note or f"Duplicated from {prompt.version}",
            created_by=prompt.created_by,
        )
        self._db.add(new_prompt)
        await self._db.commit()
        await self._db.refresh(new_prompt)

        return await self.get_prompt(new_prompt.id)