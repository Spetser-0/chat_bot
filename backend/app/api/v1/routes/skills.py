"""
app/api/v1/routes/skills.py
────────────────────────────
Public skill endpoints (Lesson 4.7).

Serves the UI skill selector. Privacy rules:
- Only is_public=True skills are listed/returned.
- `system_prompt` NEVER leaves this endpoint — it's server-internal.
- Tools are exposed as NAMES only (badges), never configs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.skill import PublicSkillResponse
from app.services.skill_resolver import SkillService

router = APIRouter(prefix="/skills", tags=["Skills"])

# No auth dependency by design: the catalog is the browseable storefront.
# Premium is a FLAG here (lock icon); enforcement happens in
# resolve_skill_for_message at chat time, not at browse time.


def _to_card(skill) -> PublicSkillResponse:
    return PublicSkillResponse(
        name=skill.name,
        slug=skill.slug,
        description=skill.description,
        is_premium=skill.is_premium,
        tools=[t.tool_name for t in skill.tools if t.is_enabled],
    )


@router.get("", response_model=list[PublicSkillResponse])
async def list_public_skills(db: AsyncSession = Depends(get_db)):
    """Catalogue of public skills for the UI selector."""
    skills = await SkillService(db).list_public_skills()
    return [_to_card(s) for s in skills]


@router.get("/{slug}", response_model=PublicSkillResponse)
async def get_public_skill(slug: str, db: AsyncSession = Depends(get_db)):
    """Single public skill card. Private/unknown → 404 (indistinguishable)."""
    skills = SkillService(db)
    skill = await skills.get_skill_by_slug(slug)  # raises NotFoundError
    return _to_card(skill)
