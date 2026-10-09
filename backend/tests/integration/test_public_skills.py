"""
tests/integration/test_public_skills.py
────────────────────────────────────────
Public skill catalogue endpoints (Lesson 4.7).
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from app.models.skill import Skill
from app.models.skill_tool import SkillTool


async def _skill(db, slug, *, public, premium=False, prompt="SECRET-PROMPT"):
    s = Skill(id=uuid.uuid4(), name=slug, slug=slug, is_public=public,
              is_premium=premium, system_prompt=prompt,
              description=f"وصف {slug}")
    db.add(s)
    await db.flush()
    db.add(SkillTool(id=uuid.uuid4(), skill_id=s.id,
                     tool_name="calculator", is_enabled=True))
    db.add(SkillTool(id=uuid.uuid4(), skill_id=s.id,
                     tool_name="web_search", is_enabled=False))
    await db.commit()
    return s


class TestPublicCatalogue:
    @pytest.mark.asyncio
    async def test_list_returns_only_public(self, client, db):
        await _skill(db, f"pub-{uuid.uuid4().hex[:6]}", public=True)
        await _skill(db, f"priv-{uuid.uuid4().hex[:6]}", public=False)
        resp = await client.get("/api/v1/skills")
        assert resp.status_code == 200
        slugs = [s["slug"] for s in resp.json()]
        assert all(not slug.startswith("priv-") for slug in slugs)

    @pytest.mark.asyncio
    async def test_card_hides_system_prompt(self, client, db):
        s = await _skill(db, f"pub-{uuid.uuid4().hex[:6]}", public=True)
        resp = await client.get(f"/api/v1/skills/{s.slug}")
        assert resp.status_code == 200
        body = resp.json()
        assert "system_prompt" not in body
        assert "SECRET-PROMPT" not in resp.text

    @pytest.mark.asyncio
    async def test_tools_are_names_only_enabled_only(self, client, db):
        s = await _skill(db, f"pub-{uuid.uuid4().hex[:6]}", public=True)
        resp = await client.get(f"/api/v1/skills/{s.slug}")
        assert resp.json()["tools"] == ["calculator"]

    @pytest.mark.asyncio
    async def test_premium_flagged_but_listed(self, client, db):
        s = await _skill(db, f"vip-{uuid.uuid4().hex[:6]}",
                         public=True, premium=True)
        resp = await client.get("/api/v1/skills")
        card = next(c for c in resp.json() if c["slug"] == s.slug)
        assert card["is_premium"] is True

    @pytest.mark.asyncio
    async def test_private_skill_get_returns_404(self, client, db):
        s = await _skill(db, f"priv-{uuid.uuid4().hex[:6]}", public=False)
        resp = await client.get(f"/api/v1/skills/{s.slug}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unknown_slug_404(self, client):
        resp = await client.get("/api/v1/skills/no-such-thing")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_no_auth_required(self, client, db):
        # catalog must be browsable pre-login for the landing page
        resp = await client.get("/api/v1/skills")
        assert resp.status_code == 200
