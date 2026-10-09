"""
app/schemas/chat.py
───────────────────
Pydantic schemas for POST /api/v1/chat/completions (Phase 3, Lesson 3.9).
"""
from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, Field, field_validator

from app.core.validation import strip_control_chars

MAX_MESSAGE_CHARS = 8_000        # hard input cap (Phase 10, Lesson 10.3 — confirmed)
MAX_HISTORY_MESSAGES = 50


class ChatCompletionRequest(BaseModel):
    """Client request body."""

    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    skill_slug: str | None = Field(default=None, max_length=50)
    stream: bool = True
    regenerate: bool = Field(
        default=False,
        description=(
            "Re-answer the last user turn without duplicating it. "
            "Requires conversation_id; the last history row must be a user message."
        ),
    )

    @field_validator("message")
    @classmethod
    def _sanitize_message(cls, v: str) -> str:
        v = strip_control_chars(v).strip()
        if not v:
            raise ValueError("الرسالة لا يمكن أن تكون فارغة.")
        if len(v) > MAX_MESSAGE_CHARS:
            raise ValueError(f"الرسالة طويلة جداً (الحد الأقصى {MAX_MESSAGE_CHARS} حرف).")
        return v

    @field_validator("skill_slug")
    @classmethod
    def _slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", v):
            raise ValueError("skill_slug بصيغة غير صالحة.")
        return v

    @field_validator("regenerate")
    @classmethod
    def _regenerate_needs_conversation(cls, v: bool, info) -> bool:
        if v and info.data.get("conversation_id") is None:
            raise ValueError("regenerate يتطلب conversation_id.")
        return v


class UsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: str
    latency_ms: float


class ChatCompletionResponse(BaseModel):
    """Non-streaming (stream=false) JSON response."""

    conversation_id: uuid.UUID
    message_id: uuid.UUID
    text: str
    provider_slug: str
    model_name: str
    skill_slug: str | None = None
    usage: UsageInfo
