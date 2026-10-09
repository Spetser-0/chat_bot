"""
app/schemas/skill.py
─────────────────────
Pydantic schemas for admin skill management (Lesson 4.6)
and public skill listing (Lesson 4.7).
"""
from __future__ import annotations

import re
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.utils.prompt_variables import ALLOWED_VARIABLES, render_prompt

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")


def _validate_slug(v: str) -> str:
    if not _SLUG_RE.fullmatch(v):
        raise ValueError("skill_slug بصيغة غير صالحة.")
    return v


def _validate_prompt_variables(prompt: str) -> str:
    """Fail closed on unknown {{variables}} at SAVE time, not at chat time."""
    dummy = {name: "x" for name in ALLOWED_VARIABLES}
    # render_prompt raises ValidationError (subclass of ValueError-safe
    # domain error) for unknown variables; pydantic surfaces it as 422.
    render_prompt(prompt, dummy)
    return prompt


class SkillToolIn(BaseModel):
    tool_name: str = Field(min_length=1, max_length=50)
    tool_config: dict | None = None
    is_enabled: bool = True


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str
    description: str | None = None
    system_prompt: str = Field(min_length=1, max_length=50_000)
    temperature: Decimal = Field(default=Decimal("0.70"), ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=200_000)
    preferred_provider_id: uuid.UUID | None = None
    fallback_provider_id: uuid.UUID | None = None
    is_public: bool = False
    is_premium: bool = False
    cost_multiplier: Decimal = Field(default=Decimal("1.00"), gt=0, le=100)
    tools: list[SkillToolIn] = Field(default_factory=list, max_length=10)

    _slug_ok = field_validator("slug")(_validate_slug)
    _prompt_ok = field_validator("system_prompt")(_validate_prompt_variables)

    @field_validator("tools")
    @classmethod
    def _tools_valid(cls, tools: list[SkillToolIn]) -> list[SkillToolIn]:
        from app.services.tool_registry import validate_tool_binding

        seen: set[str] = set()
        for t in tools:
            validate_tool_binding(t.tool_name, t.tool_config)
            if t.tool_name in seen:
                raise ValueError(f"تكرار الأداة: {t.tool_name}")
            seen.add(t.tool_name)
        return tools


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str | None = Field(default=None, min_length=1, max_length=50_000)
    temperature: Decimal | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)
    preferred_provider_id: uuid.UUID | None = None
    fallback_provider_id: uuid.UUID | None = None
    is_public: bool | None = None
    is_premium: bool | None = None
    cost_multiplier: Decimal | None = Field(default=None, gt=0, le=100)
    tools: list[SkillToolIn] | None = None  # full replacement when provided

    _prompt_ok = field_validator("system_prompt")(
        lambda cls, v: _validate_prompt_variables(v) if v is not None else v
    )

    @field_validator("tools")
    @classmethod
    def _tools_valid(cls, tools: list[SkillToolIn] | None):
        if tools is None:
            return tools
        return SkillCreate._tools_valid.__func__(cls, tools)


class SkillToolOut(BaseModel):
    id: uuid.UUID
    tool_name: str
    tool_config: dict | None
    is_enabled: bool

    model_config = {"from_attributes": True}


class SkillResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    system_prompt: str
    temperature: Decimal
    max_tokens: int
    preferred_provider_id: uuid.UUID | None
    fallback_provider_id: uuid.UUID | None
    is_public: bool
    is_premium: bool
    cost_multiplier: Decimal
    version: int
    tools: list[SkillToolOut]

    model_config = {"from_attributes": True}


class PublicSkillResponse(BaseModel):
    """Safe card for the UI selector — no system_prompt leak."""

    name: str
    slug: str
    description: str | None
    is_premium: bool
    tools: list[str]  # names only, for badges

    model_config = {"from_attributes": True}


class SkillTestRequest(BaseModel):
    sample_message: str = Field(min_length=1, max_length=2_000)


class SkillTestResponse(BaseModel):
    skill_slug: str
    rendered_system_prompt: str
    reply_text: str | None
    provider_slug: str | None
    usage: dict | None
    note: str | None = None
