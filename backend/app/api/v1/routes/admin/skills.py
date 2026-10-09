"""
app/api/v1/routes/admin/skills.py
──────────────────────────────────
Admin CRUD + test endpoint for skills (Lesson 4.6).

- Reads (`GET`): developer or admin (`get_developer`) — dashboard needs full list.
- Mutations (`POST/PATCH/DELETE`): admin only (`get_admin`).
- `POST {id}/test`: dry-run a skill; falls back to a safe mock reply when
  no provider is configured so the admin UI never 500s during editing.

NOTE: `/_meta/count` is declared BEFORE `/{skill_id}` — FastAPI route
matching is order-sensitive, and `/admin/skills/_meta/count` would
otherwise 422 trying to parse "_meta" as a UUID.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin, get_developer
from app.core.errors import ConflictError, NotFoundError
from app.db.session import get_db
from app.models.skill import Skill
from app.models.skill_tool import SkillTool
from app.models.student import Student
from app.schemas.skill import (
    SkillCreate,
    SkillResponse,
    SkillTestRequest,
    SkillTestResponse,
    SkillUpdate,
)
from app.services.llm.router import LLMRouter
from app.services.skill_resolver import SkillService

router = APIRouter(prefix="/admin/skills", tags=["Admin - Skills"])


async def _get_skill(db: AsyncSession, skill_id: uuid.UUID) -> Skill:
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if skill is None:
        raise NotFoundError("المهارة غير موجودة.")
    return skill


async def _apply_tools(db: AsyncSession, skill: Skill, tools_in) -> None:
    """Full-replace bindings. Async-safe: bulk delete instead of lazy clear()."""
    await db.execute(delete(SkillTool).where(SkillTool.skill_id == skill.id))
    for t in tools_in:
        db.add(SkillTool(
            id=uuid.uuid4(), skill_id=skill.id, tool_name=t.tool_name,
            tool_config=t.tool_config, is_enabled=t.is_enabled,
        ))


async def _audit_skill(
    db: AsyncSession, actor_id: uuid.UUID, action: str,
    skill: Skill, metadata: dict | None = None,
) -> None:
    """Write an audit_logs row for a skill mutation (Phase 8, Lesson 8.7)."""
    from app.services.admin.audit_log_service import AuditLogService
    await AuditLogService(db).log_action(
        actor_id=actor_id, action=action,
        resource_type="skill", resource_id=str(skill.id),
        metadata={"slug": skill.slug, **(metadata or {})},
    )


# ── List / Read (developer+) ─────────────────────────────────────────────

@router.get("", response_model=list[SkillResponse])
async def list_skills(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    include_private: bool = Query(True),
):
    """Dashboard listing — all skills (private included by default)."""
    stmt = select(Skill)
    if not include_private:
        stmt = stmt.where(Skill.is_public.is_(True))
    stmt = stmt.order_by(Skill.name)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/_meta/count", response_model=dict)
async def skill_count(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counts for the dashboard header."""
    total = (await db.execute(select(func.count()).select_from(Skill))).scalar_one()
    public = (await db.execute(
        select(func.count()).select_from(Skill).where(Skill.is_public.is_(True))
    )).scalar_one()
    return {"total": total, "public": public}


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: uuid.UUID,
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    return await _get_skill(db, skill_id)


# ── Mutations (admin only) ───────────────────────────────────────────────

@router.post("", status_code=201, response_model=SkillResponse)
async def create_skill(
    body: SkillCreate,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    clash = await db.execute(select(Skill.id).where(Skill.slug == body.slug))
    if clash.scalar_one_or_none() is not None:
        raise ConflictError(f"المهارة '{body.slug}' موجودة مسبقًا.")

    skill = Skill(
        id=uuid.uuid4(), name=body.name, slug=body.slug,
        description=body.description, system_prompt=body.system_prompt,
        temperature=body.temperature, max_tokens=body.max_tokens,
        preferred_provider_id=body.preferred_provider_id,
        fallback_provider_id=body.fallback_provider_id,
        is_public=body.is_public, is_premium=body.is_premium,
        cost_multiplier=body.cost_multiplier, version=1,
        created_by_user_id=admin.id,
    )
    db.add(skill)
    await db.flush()  # skill.id usable for tool bindings
    await _apply_tools(db, skill, body.tools)
    await db.commit()
    await db.refresh(skill, ["tools"])
    await _audit_skill(db, admin.id, "skill.created", skill)
    return skill


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: uuid.UUID,
    body: SkillUpdate,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    skill = await _get_skill(db, skill_id)
    # tools popped pre-dump to keep SkillToolIn objects (dump → dicts)
    tools_provided = body.tools
    data = body.model_dump(exclude_unset=True)
    data.pop("tools", None)

    for field_name, value in data.items():
        setattr(skill, field_name, value)
    if tools_provided is not None:
        await _apply_tools(db, skill, tools_provided)
    skill.version += 1
    await db.commit()
    await db.refresh(skill, ["tools"])
    await _audit_skill(db, admin.id, "skill.updated", skill,
                       {"fields": sorted(data.keys())})
    return skill


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    skill = await _get_skill(db, skill_id)
    slug, name = skill.slug, skill.name
    await db.delete(skill)
    await db.commit()
    from app.services.admin.audit_log_service import AuditLogService
    await AuditLogService(db).log_action(
        actor_id=admin.id, action="skill.deleted",
        resource_type="skill", resource_id=str(skill_id),
        metadata={"slug": slug, "name": name},
    )


@router.post("/{skill_id}/test", response_model=SkillTestResponse)
async def test_skill(
    skill_id: uuid.UUID,
    body: SkillTestRequest,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dry-run a skill. Safe path when no provider configured."""
    skill = await _get_skill(db, skill_id)
    svc = SkillService(db)

    rendered = svc.inject_user_context(skill.system_prompt, admin)
    try:
        result = await LLMRouter(db).generate(
            messages=[
                {"role": "system", "content": rendered},
                {"role": "user", "content": body.sample_message},
            ],
            capability="chat", skill=skill,
            max_tokens=min(skill.max_tokens, 512),
            temperature=float(skill.temperature),
        )
        return SkillTestResponse(
            skill_slug=skill.slug, rendered_system_prompt=rendered,
            reply_text=result.text, provider_slug=result.provider_slug,
            usage={"input_tokens": result.input_tokens,
                   "output_tokens": result.output_tokens,
                   "cost_usd": str(result.cost_usd)},
        )
    except Exception:
        return SkillTestResponse(
            skill_slug=skill.slug, rendered_system_prompt=rendered,
            reply_text="(mock) الاختبار يعمل، لكن لا يوجد مزود نشط مكوّن.",
            provider_slug=None, usage=None,
            note="no_active_provider",
        )
