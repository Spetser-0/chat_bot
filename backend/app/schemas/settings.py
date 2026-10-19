"""
app/schemas/settings.py
────────────────────────
Pydantic schemas for System Settings management.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UpdateSettingsRequest(BaseModel):
    default_new_user_credits: int | None = Field(None, ge=0)
    daily_free_credits: int | None = Field(None, ge=0)
    credits_per_message: int | None = Field(None, ge=0)


class SystemSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_new_user_credits: int
    daily_free_credits: int
    credits_per_message: int
    updated_at: datetime | None = None
