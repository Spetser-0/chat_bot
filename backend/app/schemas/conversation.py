"""
app/schemas/conversation.py
───────────────────────────
Conversation CRUD schemas (Phase 9, Lesson 9.4).

The chat UI needs to list, open, rename, archive, and delete
conversations — endpoints that did not exist before this lesson.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    """List item for the sidebar."""

    id: uuid.UUID
    title: str | None = None
    active_skill_slug: str | None = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    """One persisted chat message (detail view)."""

    id: uuid.UUID
    role: str
    content: str
    skill_slug: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationSummary):
    """Conversation with full message history."""

    messages: list[MessageOut] = Field(default_factory=list)


class ConversationUpdateRequest(BaseModel):
    """Partial update: rename and/or archive toggle."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    is_archived: bool | None = None


class ConversationDeleteResponse(BaseModel):
    """Hard-delete confirmation."""

    deleted: bool
    conversation_id: uuid.UUID
