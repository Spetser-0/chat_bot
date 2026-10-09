"""
app/api/v1/routes/chat.py
──────────────────────────
POST /api/v1/chat/completions — unified chat endpoint (Phase 3, Lesson 3.9).

Flow:
1. Auth (active student) + schema validation.
2. Resolve/create conversation; load history (capped).
3. Resolve skill (optional); invalid slug → invalid_skill error.
4. Route through LLMRouter — stream=true → SSE, stream=false → JSON.
5. Persist user + assistant messages with usage metadata.

Credit charging/reservation is Phase 5 — this endpoint records usage
only (cost is computed and stored on the assistant message row).
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import rate_limit_chat
from app.core.errors import (
    AuthorizationError,
    NotFoundError,
    ProviderError,
    RoutingError,
    ValidationError,
)
from app.core.metrics import get_metrics
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.skill import Skill
from app.models.student import Student
from app.schemas.chat import (
    MAX_HISTORY_MESSAGES,
    ChatCompletionRequest,
    ChatCompletionResponse,
    UsageInfo,
)
from app.services.llm.router import LLMRouter
from app.services.skill_resolver import SkillService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


async def _resolve_conversation(
    db: AsyncSession, student: Student, body: ChatCompletionRequest
) -> Conversation:
    """Load owned conversation or create a new one."""
    if body.conversation_id is None:
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=student.id,
            title=body.message[:80],
            active_skill_slug=body.skill_slug,
        )
        db.add(conv)
        await db.flush()
        return conv

    result = await db.execute(
        select(Conversation).where(Conversation.id == body.conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise NotFoundError("المحادثة غير موجودة.")
    if conv.user_id != student.id:
        raise AuthorizationError("ليس لديك إذن للوصول إلى هذه المحادثة.")
    if conv.is_archived:
        raise AuthorizationError("هذه المحادثة مؤرشفة.")
    return conv


async def _resolve_skill(db: AsyncSession, slug: str | None,
                         student: Student,
                         message_text: str = "") -> Skill | None:
    """Explicit skill, 'auto' classification (Lesson 4.5), or None."""
    from app.services.skill_resolver import AUTO_SKILL_SENTINEL, SkillService

    svc = SkillService(db)
    if slug == AUTO_SKILL_SENTINEL:
        return await svc.classify_skill(message_text, student)
    if slug is None:
        return None
    return await svc.resolve_skill_for_message(slug, student)


async def _load_history(db: AsyncSession, conv: Conversation) -> list[dict]:
    """Last N messages as LLM message dicts (user/assistant only)."""
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conv.id,
            Message.role.in_([MessageRole.USER, MessageRole.ASSISTANT]),
        )
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    rows = list(result.scalars().all())
    rows.reverse()
    return [{"role": m.role, "content": m.content} for m in rows]


async def _persist_assistant(
    db: AsyncSession,
    conv: Conversation,
    *,
    text: str,
    skill_slug: str | None,
    provider_slug: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd,
    latency_ms: float,
) -> Message:
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content=text,
        skill_slug=skill_slug,
        provider_name=provider_slug,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_credits=cost_usd,  # USD until Phase 5 credit conversion
        latency_ms=int(latency_ms),
    )
    db.add(msg)
    await db.flush()
    return msg


@router.post("/completions", response_model=ChatCompletionResponse | None)
async def create_completion(
    body: ChatCompletionRequest,
    student: Student = Depends(rate_limit_chat),
    db: AsyncSession = Depends(get_db),
):
    """Chat completion: JSON when stream=false, SSE when stream=true.

    regenerate=True re-answers the last user turn without inserting a
    duplicate user Message row (Phase 9, Lesson 9.10 fix).
    """
    conv = await _resolve_conversation(db, student, body)
    history = await _load_history(db, conv)

    if body.regenerate:
        if not history or history[-1]["role"] != "user":
            raise ValidationError(
                "لا يوجد سؤال سابق لإعادة توليده في هذه المحادثة.")
        # Reuse the persisted last user turn; do not append another copy.
        message_text = history[-1]["content"]
    else:
        message_text = body.message

    skill = await _resolve_skill(db, body.skill_slug, student, message_text)
    skills = SkillService(db)

    if body.regenerate:
        # Last history row is the user turn we are re-asking.
        messages = skills.build_messages(
            skill=skill, history=history[:-1], user_message=message_text,
            student=student,
        )
    else:
        messages = skills.build_messages(
            skill=skill, history=history, user_message=message_text,
            student=student,
        )

    if skill is not None and conv.active_skill_slug != skill.slug:
        conv.active_skill_slug = skill.slug

    if not body.regenerate:
        # Persist the user turn immediately (skipped on regenerate — already stored).
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=MessageRole.USER,
            content=message_text,
            skill_slug=(skill.slug if skill else None),
        )
        db.add(user_msg)
        await db.flush()

    # ── Credit gate (Lesson 5.6): must be able to afford a minimal call ──
    from app.services.credit_service import CreditService
    from app.services.provider_service import ProviderService

    credits = CreditService(db, student)
    if body.skill_slug and skill is not None:
        # estimate: 1 output token at skill multiplier is the floor
        active = await ProviderService(db).list_active()
        if active:
            floor = await credits.calculate_message_cost(
                active[0], input_tokens=1, output_tokens=1, skill=skill)
            await credits.assert_enough_credits(floor)

    router = LLMRouter(db)
    max_tokens = skill.max_tokens if skill else None
    temperature = float(skill.temperature) if skill else None

    if body.stream:
        return StreamingResponse(
            _sse_stream(router, db, conv, messages, skill, body,
                        max_tokens, temperature, student),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Non-streaming ────────────────────────────────────────────────
    try:
        result = await router.generate(
            messages=messages,
            capability="chat",
            skill=skill,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except (RoutingError, ProviderError):
        logger.warning("chat_completion_failed", student_id=str(student.id),
                       skill=body.skill_slug)
        get_metrics().record_llm_call(
            provider=None, success=False, latency_ms=0.0)
        raise ProviderError("مزود الذكاء الاصطناعي غير متاح حالياً. حاول لاحقاً.")

    get_metrics().record_llm_call(
        provider=result.provider_slug,
        success=True,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )

    assistant = await _persist_assistant(
        db, conv, text=result.text, skill_slug=(skill.slug if skill else None),
        provider_slug=result.provider_slug, model_name=result.model_name,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_usd=result.cost_usd, latency_ms=result.latency_ms,
    )
    # ── Charge actual cost (Lesson 5.6): only after success ─────────
    await _charge_for_message(db, student, skill, assistant, body.skill_slug)
    await db.commit()
    return ChatCompletionResponse(
        conversation_id=conv.id,
        message_id=assistant.id,
        text=result.text,
        provider_slug=result.provider_slug,
        model_name=result.model_name,
        skill_slug=(skill.slug if skill else None),
        usage=UsageInfo(
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=str(result.cost_usd),
            latency_ms=result.latency_ms,
        ),
    )


async def _sse_stream(router, db, conv, messages, skill, body,
                      max_tokens, temperature, student):
    """Yield SSE frames; persist assistant row on successful completion."""
    chunks: list[str] = []
    done: dict | None = None
    # Announce conversation binding so clients can correlate the stream.
    from app.services.llm.router import StreamEvent

    yield StreamEvent("conversation", {"conversation_id": str(conv.id)}).to_sse()
    try:
        async for event in router.stream_complete(
            messages=messages,
            skill=skill,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            if event.type == "chunk":
                chunks.append(event.data["text"])
            elif event.type == "done":
                done = event.data
                get_metrics().record_llm_call(
                    provider=done.get("provider_slug"),
                    success=True,
                    latency_ms=float(done.get("latency_ms", 0.0) or 0.0),
                    input_tokens=int(done.get("input_tokens", 0) or 0),
                    output_tokens=int(done.get("output_tokens", 0) or 0),
                )
            yield event.to_sse()
    except Exception:
        logger.exception("chat_stream_unexpected_error")

        yield StreamEvent("error", {
            "code": "internal_error",
            "message": "حدث خطأ غير متوقع.",
        }).to_sse()
        await db.rollback()
        return

    if done is not None:
        assistant = await _persist_assistant(
            db, conv, text="".join(chunks), skill_slug=(skill.slug if skill else None),
            provider_slug=done["provider_slug"], model_name=done["model_name"],
            input_tokens=done["input_tokens"],
            output_tokens=done["output_tokens"],
            cost_usd=done["cost_usd"], latency_ms=done["latency_ms"],
        )
        await _charge_for_message(db, student, skill, assistant, body.skill_slug)
        await db.commit()
    else:
        await db.rollback()


async def _charge_for_message(db, student, skill, assistant: Message,
                              requested_slug: str | None) -> None:
    """Convert message cost to credits and spend. Idempotent per message.

    Policy: failed/partial calls keep any prior reservation pattern for
    Phase-10 hardening; today we charge ONLY after a complete answer.
    """
    from app.services.credit_service import CreditService
    from app.services.provider_service import ProviderService

    providers = ProviderService(db)
    try:
        provider = await providers.get_by_slug(assistant.provider_name)
    except Exception:
        logger.warning("credit_charge_skip_no_provider",
                       provider=assistant.provider_name)
        return

    credits = CreditService(db, student)
    cost = await credits.calculate_message_cost(
        provider, input_tokens=assistant.input_tokens or 0,
        output_tokens=assistant.output_tokens or 0, skill=skill,
    )
    if cost <= 0:
        return
    # Idempotency: message id is unique, so retries never double-charge.
    await credits.spend_credits(
        cost, description=f"chat:{requested_slug or 'assistant'}",
        reference_type="message", reference_id=assistant.id,
        idempotency_key=f"chat-msg-{assistant.id}",
    )
