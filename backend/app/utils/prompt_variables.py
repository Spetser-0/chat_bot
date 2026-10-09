"""
app/utils/prompt_variables.py
──────────────────────────────
Safe {{variable}} substitution for skill system prompts (Lesson 4.3).

Child analogy: the system prompt is a letter with blanks — "Dear ___".
We only fill blanks we recognise, from a fixed list, and we never let a
filled-in answer create new blanks (no double rendering).

Safety rules:
- Variables come ONLY from the caller-supplied context — untrusted user
  text never becomes a template.
- Unknown {{variables}} fail closed (ValidationError) so a typo in an
  admin's prompt 4.6-tests loudly instead of silently shipping.
- Single pass: substituted values are never re-scanned for {{…}}.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core.errors import ValidationError

if TYPE_CHECKING:
    from app.models.student import Student

_VAR_PATTERN = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")

# Canonical variables advertised to skill authors (docs/AI_SKILLS.md).
ALLOWED_VARIABLES = (
    "user_name",
    "language",
    "current_date",
    "subscription_tier",
    "course_level",
)


def render_prompt(template: str, context: dict[str, Any]) -> str:
    """Substitute {{variables}} from context. Unknown → ValidationError.

    Values are stringified; None renders as empty string.
    """

    def _sub(match: re.Match) -> str:
        name = match.group(1)
        if name not in ALLOWED_VARIABLES:
            raise ValidationError(f"متغير غير معروف في الموجه: {{{{{name}}}}}")
        value = context.get(name)
        return "" if value is None else str(value)

    return _VAR_PATTERN.sub(_sub, template)


def build_student_context(student: "Student") -> dict[str, Any]:
    """Derive template variables from a Student row.

    - user_name: display_name, falling back to email local-part.
    - subscription_tier: 'premium' if active premium else 'free'.
    - language / course_level: reserved for profile fields — defaults
      Arabic 'ar_Spetser' until the profile table lands.
    - current_date: UTC ISO date (clear for Arab users; formatted later).
    """
    name = student.display_name or student.email.split("@", 1)[0]
    tier = "premium" if getattr(student, "is_premium", False) else "free"
    return {
        "user_name": name,
        "language": getattr(student, "preferred_language", None) or "ar",
        "current_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "subscription_tier": tier,
        "course_level": getattr(student, "course_level", None) or "university",
    }
