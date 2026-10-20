"""
app/schemas/api_key.py
──────────────────────
Pydantic schemas for Developer Panel API keys.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    system_prompt: str | None = Field(None, max_length=10000)
    max_credits_per_day: int | None = Field(None, ge=0)
    allowed_skills: list[str] | None = Field(None, max_length=100)
    expires_at: datetime | None = None


class UpdateAPIKeyRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    system_prompt: str | None = Field(None, max_length=10000)
    max_credits_per_day: int | None = Field(None, ge=0)
    allowed_skills: list[str] | None = Field(None, max_length=100)
    is_active: bool | None = None
    expires_at: datetime | None = None


class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    system_prompt: str | None = None
    max_credits_per_day: int | None = None
    allowed_skills: list[str] | None = None
    is_active: bool
    expires_at: datetime | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    total_requests: int = 0


class APIKeyCreateResponse(APIKeyResponse):
    plain_key: str  # Only returned upon creation/regeneration
