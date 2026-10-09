"""
app/api/v1/routes/conversations.py
──────────────────────────────────
Conversation CRUD for the chat sidebar (Phase 9, Lesson 9.4).

Endpoints (all require an active student; ownership enforced):
- GET    /api/v1/conversations               — list (recent first; ?include_archived=true)
- GET    /api/v1/conversations/{id}          — detail with messages
- PATCH  /api/v1/conversations/{id}          — rename title / toggle is_archived
- DELETE /api/v1/conversations/{id}          — hard-delete conversation + messages
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_active_student
from app.core.errors import AuthorizationError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.student import Student
from app.schemas.conversation import (
    ConversationDeleteResponse,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdateRequest,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


async def _get_owned(
    db: AsyncSession, student: Student, conversation_id: uuid.UUID
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise NotFoundError("المحادثة غير موجودة.")
    if conv.user_id != student.id:
        raise AuthorizationError("ليس لديك إذن للوصول إلى هذه المحادثة.")
    return conv


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    include_archived: bool = Query(
        default=False, description="Include archived conversations."
    ),
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    """List the current student's conversations, most recently updated first."""
    query = select(Conversation).where(Conversation.user_id == student.id)
    if not include_archived:
        query = query.where(Conversation.is_archived.is_(False))
    query = query.order_by(Conversation.updated_at.desc()).limit(100)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    """Conversation detail with full message history (chronological order)."""
    conv = await _get_owned(db, student, conversation_id)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conv.id)
        .options(selectinload(Conversation.messages))
    )
    loaded = result.scalar_one()
    return loaded


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdateRequest,
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    """Rename (title) and/or archive/unarchive the conversation."""
    if body.title is None and body.is_archived is None:
        raise ValidationError("لا توجد حقول للتحديث.")
    conv = await _get_owned(db, student, conversation_id)
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise ValidationError("العنوان لا يمكن أن يكون فارغاً.")
        conv.title = title
    if body.is_archived is not None:
        conv.is_archived = body.is_archived
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conversation_id}", response_model=ConversationDeleteResponse)
async def delete_conversation(
    conversation_id: uuid.UUID,
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete an owned conversation (messages cascade)."""
    conv = await _get_owned(db, student, conversation_id)
    await db.delete(conv)  # ORM cascade removes messages
    await db.commit()
    return ConversationDeleteResponse(deleted=True, conversation_id=conv.id)
