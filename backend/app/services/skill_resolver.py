"""
app/services/skill_resolver.py
───────────────────────────────
SkillService — resolves and validates AI skills for chat (Phase 4, Lesson 4.1).

Child analogy: a skill is a costume for the AI (math teacher, code
reviewer…). This service is the wardrobe keeper: it finds the costume,
checks the user is allowed to wear it (public/premium), and hands out the
list of tools pinned to it. Prompt rendering with {{variables}} arrives in
Lessons 4.2–4.3; this file provides the safe lookup and access rules.

Access rules:
- Private skills (is_public=false) are invisible to `list_public_skills`
  and raise NotFoundError in `get_skill_by_slug` unless allow_private=True
  (admin/dashboard paths).
- Premium skills require student.is_premium (active flag; expiry check
  lands with subscription handling in Phase 5/6).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthorizationError, NotFoundError
from app.models.skill import Skill
from app.models.skill_tool import SkillTool
from app.models.student import Student

# Safe default when no skill is selected (Lesson 4.5 will make this routed).
DEFAULT_SKILL_SLUG = "general_assistant"
# Sentinel a client may send to request automatic classification (Mode B).
AUTO_SKILL_SENTINEL = "auto"

_CLASSIFIER_PROMPT = """أنت مصنّف رسائل. اختر المهارة الأنسب لرسالة الطالب من القائمة فقط.
أجب باسم المهارة (slug) فقط، بدون شرح وبدون علامات ترقيم.
المهارات المتاحة:
{skills}
إذا لم تناسب أي مهارة الرسالة أجب: {default}"""


class SkillService:
    """Lookup + access control + tool list for skills."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Lookups ────────────────────────────────────────────────────────
    async def get_skill_by_slug(
        self, slug: str, *, allow_private: bool = False
    ) -> Skill:
        """Fetch a skill by slug; invisible privates → NotFoundError."""
        result = await self._db.execute(select(Skill).where(Skill.slug == slug))
        skill = result.scalar_one_or_none()
        if skill is None or (not skill.is_public and not allow_private):
            # Deliberately indistinguishable: don't confirm private slugs exist.
            raise NotFoundError("المهارة المطلوبة غير موجودة.")
        return skill

    async def list_public_skills(self) -> list[Skill]:
        """All public skills ordered by name (for the UI selector)."""
        result = await self._db.execute(
            select(Skill).where(Skill.is_public.is_(True)).order_by(Skill.name)
        )
        return list(result.scalars().all())

    async def resolve_skill_for_message(
        self, slug: str | None, student: Student
    ) -> Skill | None:
        """Validate a user-chosen skill for a chat message.

        None → caller uses no skill (plain assistant). Raises:
        NotFoundError for unknown/private slug; AuthorizationError when a
        premium skill is requested by a non-premium student.
        """
        if slug is None:
            return None
        skill = await self.get_skill_by_slug(slug)
        if skill.is_premium and not student.is_premium:
            raise AuthorizationError(
                "هذه المهارة متاحة للمشتركين في الباقة المميزة فقط."
            )
        return skill

    # ── Prompt assembly (Lesson 4.2 + variables 4.3) ───────────────────
    # Rough heuristic: ~4 characters per token for mixed Arabic/English.
    _CHARS_PER_TOKEN = 4

    def build_system_prompt(self, skill: Skill) -> str:
        """Return the skill's system prompt verbatim (rendering via
        inject_user_context / build_messages)."""
        return skill.system_prompt

    def inject_user_context(self, prompt: str, student: Student) -> str:
        """Render {{variables}} in a system prompt from the student row.

        Unknown variables raise ValidationError (fail closed) — see
        app/utils/prompt_variables.py for the safety rules.
        """
        from app.utils.prompt_variables import build_student_context, render_prompt

        return render_prompt(prompt, build_student_context(student))

    def build_messages(
        self,
        *,
        skill: Skill | None,
        history: list[dict[str, str]],
        user_message: str,
        student: Student | None = None,
    ) -> list[dict[str, str]]:
        """Assemble the final LLM message list.

        Order (per spec):
        1. System prompt from the skill, variables rendered (if any).
        2. Conversation history, trimmed to fit the model's token budget.
        3. The current user message (never trimmed).
        """
        messages: list[dict[str, str]] = []
        if skill is not None:
            prompt = skill.system_prompt
            if student is not None:
                prompt = self.inject_user_context(prompt, student)
            messages.append({"role": "system", "content": prompt})

        budget_chars = self._history_budget_chars(skill)
        kept = self._trim_history(history, budget_chars)
        messages.extend(kept)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _history_budget_chars(self, skill: Skill | None) -> int:
        if skill is None:
            return 120_000
        # Reserve ~20% of max_tokens for the completion + system prompt.
        budget_tokens = int(skill.max_tokens * 0.8)
        return max(budget_tokens, 256) * self._CHARS_PER_TOKEN

    @classmethod
    def _est_chars(cls, msg: dict[str, str]) -> int:
        return len(msg.get("content", ""))

    def _trim_history(
        self, history: list[dict[str, str]], budget_chars: int
    ) -> list[dict[str, str]]:
        """Keep the newest messages that fit the char budget."""
        kept: list[dict[str, str]] = []
        used = 0
        for msg in reversed(history):
            size = self._est_chars(msg)
            if used + size > budget_chars and kept:
                break
            kept.insert(0, msg)
            used += size
        return kept

    # ── Tools ──────────────────────────────────────────────────────────
    async def get_allowed_tools(self, skill: Skill) -> list[SkillTool]:
        """Enabled tools bound to a skill. Execution is NOT allowed here —
        no tool is ever run without the sandbox (Lesson 4.4)."""
        result = await self._db.execute(
            select(SkillTool).where(
                SkillTool.skill_id == skill.id, SkillTool.is_enabled.is_(True)
            )
        )
        return list(result.scalars().all())

    # ── Routing modes (Lesson 4.5) ─────────────────────────────────────
    async def classify_skill(
        self, text: str, student: Student
    ) -> Skill | None:
        """Mode B: pick a public skill slug via a cheap LLM call.

        Guarantees a VALID choice or falls back:
        - Unknown junk from the model → DEFAULT_SKILL_SLUG
        - Skill the student can't access (premium/private) → treat as
          default rule: resolve_skill_for_message still applies.
        - Classifier errors / no providers → DEFAULT_SKILL_SLUG
        - Default skill missing → None (plain assistant)
        """
        import re

        import structlog

        log = structlog.get_logger(__name__)

        slugs = [s.slug for s in await self.list_public_skills()]
        if not slugs:
            return None

        prompt = _CLASSIFIER_PROMPT.format(
            skills="\n".join(f"- {s}" for s in slugs), default=DEFAULT_SKILL_SLUG
        )
        try:
            # Late import: SkillService must not hard-depend on the router.
            from app.services.llm.router import LLMRouter

            result = await LLMRouter(self._db).generate(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text[:2000]},
                ],
                capability="chat", max_tokens=20, temperature=0.0,
            )
            guess = re.sub(r"[^a-z0-9_-]", "", result.text.strip().lower())
            slug = guess if guess in slugs else DEFAULT_SKILL_SLUG
        except Exception as exc:  # any classifier failure → default
            log.warning("skill_classification_fallback", error=type(exc).__name__)
            slug = DEFAULT_SKILL_SLUG

        # Resolve through the SAME gates users face (premium/private);
        # on Forbidden/NotFound fall back to the default skill.
        for candidate in (slug, DEFAULT_SKILL_SLUG):
            try:
                return await self.resolve_skill_for_message(candidate, student)
            except (NotFoundError, AuthorizationError):
                continue
        return None
