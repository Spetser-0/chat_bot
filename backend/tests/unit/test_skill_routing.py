"""
tests/unit/test_skill_routing.py
─────────────────────────────────
Lesson 4.5 — Mode B automatic skill classification via the LLM router.
litellm.acompletion is monkeypatched; classification must always yield
a valid accessible skill, the default skill, or None.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import litellm
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import encrypt_secret
from app.db.session import Base
from app.models.ai_provider import AIProvider
from app.models.skill import Skill
from app.models.student import Student
from app.services.skill_resolver import DEFAULT_SKILL_SLUG, SkillService


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _setup(db, *, classifier_answer: str, extra_skills=()):
    db.add(AIProvider(
        id=uuid.uuid4(), slug="cls-provider", name="p", model_name="m",
        api_key_encrypted=encrypt_secret("sk-x"), is_active=True,
        priority_weight=100, max_retries=1, timeout_seconds=5,
        cost_input_per_1k=Decimal("0.001"), cost_output_per_1k=Decimal("0.002"),
    ))
    for slug, premium in [("math-tutor", False), ("vip-coach", True),
                          (DEFAULT_SKILL_SLUG, False), *extra_skills]:
        db.add(Skill(id=uuid.uuid4(), name=slug, slug=slug, is_public=True,
                     is_premium=premium, system_prompt=f"prompt:{slug}"))
    student = Student(
        id=uuid.uuid4(), email=f"u{uuid.uuid4().hex[:6]}@t.com",
        role="student", status="active", credit_balance=0, is_premium=False,
    )
    db.add(student)
    await db.commit()
    return student


def _mock_llm(text):
    return AsyncMock(return_value=SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
    ))


class TestAutoClassification:
    @pytest.mark.asyncio
    async def test_valid_slug_picked(self, db, monkeypatch):
        student = await _setup(db, classifier_answer="math-tutor")
        monkeypatch.setattr(litellm, "acompletion", _mock_llm("math-tutor"))
        skill = await SkillService(db).classify_skill("علّمني الجمع", student)
        assert skill.slug == "math-tutor"

    @pytest.mark.asyncio
    async def test_junk_output_falls_back_to_default(self, db, monkeypatch):
        student = await _setup(db, classifier_answer="nope")
        monkeypatch.setattr(litellm, "acompletion", _mock_llm("لا يوجد!"))
        skill = await SkillService(db).classify_skill("شيء ما", student)
        assert skill.slug == DEFAULT_SKILL_SLUG

    @pytest.mark.asyncio
    async def test_classifier_exception_falls_back(self, db, monkeypatch):
        student = await _setup(db, classifier_answer="boom")

        async def dead(**kw):
            raise litellm.Timeout("t", model="m", llm_provider="x")

        monkeypatch.setattr(litellm, "acompletion", dead)
        skill = await SkillService(db).classify_skill("سؤال", student)
        assert skill.slug == DEFAULT_SKILL_SLUG

    @pytest.mark.asyncio
    async def test_premium_skill_never_routed_for_free_user(self, db, monkeypatch):
        student = await _setup(db, classifier_answer="vip-coach")
        monkeypatch.setattr(litellm, "acompletion", _mock_llm("vip-coach"))
        skill = await SkillService(db).classify_skill("اريد التميز", student)
        assert skill.slug == DEFAULT_SKILL_SLUG  # gated → default, not premium

    @pytest.mark.asyncio
    async def test_no_public_skills_returns_none(self, db, monkeypatch):
        student = Student(id=uuid.uuid4(), email="a@b.c", role="student",
                          status="active", credit_balance=0, is_premium=False)
        db.add(student)
        await db.commit()
        assert await SkillService(db).classify_skill("hi", student) is None
