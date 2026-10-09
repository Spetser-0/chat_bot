"""
tests/unit/test_skill_service.py
─────────────────────────────────
Unit tests for SkillService (Lesson 4.1): lookups, access rules, tools.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import AuthorizationError, NotFoundError
from app.db.session import Base
from app.models.skill import Skill
from app.models.skill_tool import SkillTool
from app.models.student import Student
from app.services.skill_resolver import SkillService


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _student(db, *, premium=False) -> Student:
    s = Student(
        id=uuid.uuid4(), email=f"u{uuid.uuid4().hex[:6]}@t.com",
        display_name="طالب", role="student", status="active",
        credit_balance=0, is_premium=premium,
    )
    db.add(s)
    await db.commit()
    return s


async def _skill(db, slug, *, public=True, premium=False,
                 prompt="أنت مساعد مفيد.") -> Skill:
    sk = Skill(id=uuid.uuid4(), name=slug, slug=slug, system_prompt=prompt,
               is_public=public, is_premium=premium)
    db.add(sk)
    await db.commit()
    return sk


class TestLookup:
    @pytest.mark.asyncio
    async def test_public_skill_found(self, db):
        await _skill(db, "math-tutor")
        found = await SkillService(db).get_skill_by_slug("math-tutor")
        assert found.slug == "math-tutor"

    @pytest.mark.asyncio
    async def test_unknown_slug_raises(self, db):
        with pytest.raises(NotFoundError):
            await SkillService(db).get_skill_by_slug("nope")

    @pytest.mark.asyncio
    async def test_private_skill_hidden_from_users(self, db):
        await _skill(db, "secret", public=False)
        with pytest.raises(NotFoundError):
            await SkillService(db).get_skill_by_slug("secret")

    @pytest.mark.asyncio
    async def test_private_skill_visible_with_allow_private(self, db):
        await _skill(db, "secret", public=False)
        found = await SkillService(db).get_skill_by_slug("secret", allow_private=True)
        assert found.slug == "secret"

    @pytest.mark.asyncio
    async def test_list_public_skills_excludes_private(self, db):
        await _skill(db, "pub", public=True)
        await _skill(db, "priv", public=False)
        slugs = [s.slug for s in await SkillService(db).list_public_skills()]
        assert slugs == ["pub"]


class TestResolveForMessage:
    @pytest.mark.asyncio
    async def test_none_slug_returns_none(self, db):
        student = await _student(db)
        assert await SkillService(db).resolve_skill_for_message(None, student) is None

    @pytest.mark.asyncio
    async def test_free_skill_ok_for_free_student(self, db):
        await _skill(db, "math-tutor")
        student = await _student(db, premium=False)
        skill = await SkillService(db).resolve_skill_for_message("math-tutor", student)
        assert skill.slug == "math-tutor"

    @pytest.mark.asyncio
    async def test_premium_skill_rejected_for_free_student(self, db):
        await _skill(db, "law-advisor", premium=True)
        student = await _student(db, premium=False)
        with pytest.raises(AuthorizationError):
            await SkillService(db).resolve_skill_for_message("law-advisor", student)

    @pytest.mark.asyncio
    async def test_premium_skill_ok_for_premium_student(self, db):
        await _skill(db, "law-advisor", premium=True)
        student = await _student(db, premium=True)
        skill = await SkillService(db).resolve_skill_for_message("law-advisor", student)
        assert skill.is_premium


class TestTools:
    @pytest.mark.asyncio
    async def test_only_enabled_tools_returned(self, db):
        skill = await _skill(db, "math-tutor")
        db.add(SkillTool(id=uuid.uuid4(), skill_id=skill.id,
                         tool_name="calculator", is_enabled=True))
        db.add(SkillTool(id=uuid.uuid4(), skill_id=skill.id,
                         tool_name="web_search", is_enabled=False))
        await db.commit()
        tools = await SkillService(db).get_allowed_tools(skill)
        assert [t.tool_name for t in tools] == ["calculator"]

    @pytest.mark.asyncio
    async def test_prompt_without_variables_passthrough(self, db):
        skill = await _skill(db, "math-tutor", prompt="علّم الرياضيات.")
        svc = SkillService(db)
        assert svc.build_system_prompt(skill) == "علّم الرياضيات."
        student = await _student(db)
        assert svc.inject_user_context(skill.system_prompt, student) == "علّم الرياضيات."


class TestPromptBuilding:
    """Lesson 4.2 — message assembly and history trimming."""

    @staticmethod
    def _svc(db) -> SkillService:
        return SkillService(db)

    @pytest.mark.asyncio
    async def test_system_then_history_then_user(self, db):
        skill = await _skill(db, "math-tutor", prompt="SYS")
        history = [{"role": "user", "content": "q1"},
                   {"role": "assistant", "content": "a1"}]
        msgs = self._svc(db).build_messages(
            skill=skill, history=history, user_message="q2")
        assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
        assert msgs[0]["content"] == "SYS"
        assert msgs[-1]["content"] == "q2"

    @pytest.mark.asyncio
    async def test_no_skill_no_system_message(self, db):
        msgs = self._svc(db).build_messages(
            skill=None, history=[{"role": "user", "content": "q1"}],
            user_message="q2")
        assert msgs[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_history_trimmed_to_budget_oldest_first(self, db):
        # max_tokens=100 → budget = min 256*4=1024 chars… use huge history
        skill = await _skill(db, "tiny")
        skill.max_tokens = 320  # 256-token budget floor → 1024 chars
        big = "x" * 300
        history = [{"role": "user", "content": big} for _ in range(10)]
        msgs = self._svc(db).build_messages(
            skill=skill, history=history, user_message="now")
        # ~1024-char budget: keeps ~3 newest (300 each), drops oldest
        history_kept = msgs[1:-1]
        assert len(history_kept) == 3
        assert all(m["content"] == big for m in history_kept)

    @pytest.mark.asyncio
    async def test_single_oversized_message_still_kept(self, db):
        skill = await _skill(db, "tiny")
        skill.max_tokens = 320
        history = [{"role": "user", "content": "y" * 5000}]
        msgs = self._svc(db).build_messages(
            skill=skill, history=history, user_message="now")
        # never returns empty history if that drops ALL context unfairly —
        # the single newest message is always kept
        assert msgs[1:-1][0]["content"] == "y" * 5000

    @pytest.mark.asyncio
    async def test_empty_history(self, db):
        skill = await _skill(db, "math-tutor", prompt="SYS")
        msgs = self._svc(db).build_messages(
            skill=skill, history=[], user_message="hi")
        assert [m["role"] for m in msgs] == ["system", "user"]


class TestDynamicVariables:
    """Lesson 4.3 — {{variable}} rendering via app.utils.prompt_variables."""

    @pytest.mark.asyncio
    async def test_all_variables_render(self, db):
        from datetime import datetime, timezone

        student = await _student(db, premium=True)
        student.display_name = "سارة"
        skill = await _skill(db, "s", prompt=(
            "مرحباً {{user_name}}! اللغة {{language}}، التاريخ {{current_date}}،"
            " الباقة {{subscription_tier}}، المستوى {{course_level}}."))
        out = SkillService(db).inject_user_context(skill.system_prompt, student)
        assert "سارة" in out
        assert "اللغة ar" in out
        # Same source of truth as implementation (UTC calendar day)
        assert datetime.now(timezone.utc).strftime("%Y-%m-%d") in out
        assert "الباقة premium" in out
        assert "المستوى university" in out

    @pytest.mark.asyncio
    async def test_unknown_variable_fails_closed(self, db):
        from app.core.errors import ValidationError

        student = await _student(db)
        skill = await _skill(db, "s", prompt="hello {{hacker_field}}")
        with pytest.raises(ValidationError):
            SkillService(db).inject_user_context(skill.system_prompt, student)

    @pytest.mark.asyncio
    async def test_no_double_rendering(self, db):
        """A variable VALUE containing {{...}} must not be re-rendered."""
        student = await _student(db)
        student.display_name = "{{language}}"
        skill = await _skill(db, "s", prompt="name={{user_name}}")
        out = SkillService(db).inject_user_context(skill.system_prompt, student)
        assert out == "name={{language}}"

    @pytest.mark.asyncio
    async def test_whitespace_inside_braces_ok(self, db):
        student = await _student(db)
        skill = await _skill(db, "s", prompt="أهلاً {{ user_name }}")
        out = SkillService(db).inject_user_context(skill.system_prompt, student)
        assert out == f"أهلاً {student.display_name}"

    @pytest.mark.asyncio
    async def test_build_messages_renders_system_prompt(self, db):
        student = await _student(db)
        skill = await _skill(db, "s", prompt="أنت معلم {{user_name}}.")
        msgs = SkillService(db).build_messages(
            skill=skill, history=[], user_message="hi", student=student)
        assert msgs[0]["content"] == f"أنت معلم {student.display_name}."

    @pytest.mark.asyncio
    async def test_display_name_fallback_to_email(self, db):
        student = await _student(db)
        student.display_name = None
        skill = await _skill(db, "s", prompt="[{{user_name}}]")
        out = SkillService(db).inject_user_context(skill.system_prompt, student)
        assert out == f"[{student.email.split('@')[0]}]"
