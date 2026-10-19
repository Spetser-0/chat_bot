"""
app/services/settings_service.py
────────────────────────────────
Global system settings service for default credits and quotas.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_settings import SystemSettings


class SettingsService:
    """Manages global system settings singleton."""

    async def get_settings(self, db: AsyncSession) -> SystemSettings:
        result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
        settings = result.scalar_one_or_none()

        if not settings:
            settings = SystemSettings(
                id=1,
                default_new_user_credits=300,
                daily_free_credits=300,
                credits_per_message=1,
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return settings

    async def update_settings(self, db: AsyncSession, **updates) -> SystemSettings:
        settings = await self.get_settings(db)

        allowed_fields = {
            "default_new_user_credits",
            "daily_free_credits",
            "credits_per_message",
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(settings, field, value)

        settings.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(settings)
        return settings


settings_service = SettingsService()
