"""
app/services/intent_router.py
──────────────────────────────
Lightweight intent classifier for ambiguous user requests.

Returns feature intent, confidence, tier, and clarification question.
Does NOT hardcode provider names — only returns feature + tier.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class IntentResult:
    """Result of intent classification."""
    intent: Literal["chat", "presentation", "research", "question_solver", "unknown"]
    confidence: float
    model_tier: Literal["fast", "default", "thinker"]
    requires_clarification: bool
    clarifying_question: str | None


# Arabic/English keywords for each feature
_PRESENTATION_KEYWORDS = [
    "عرض", "تقديم", "presentation", "slides", "شرائح", "بوربوينت", "powerpoint",
    "سلايد", "slide", "تصميم عرض", "انشاء عرض", "create presentation",
]

_RESEARCH_KEYWORDS = [
    "بحث", "research", "مراجع", "مصادر", "citations", "أكاديمي", "academic",
    "دراسة", "study", "مراجعة أدب", "literature review", "أطروحة", "thesis",
]

_QUESTION_SOLVER_KEYWORDS = [
    "حل", "solve", "مسألة", "problem", "معادلة", "equation", "تمرين", "exercise",
    "سؤال", "question", "خطوة بخطوة", "step by step", "اشتقاق", "derivation",
    "تكامل", "integral", "تفاضل", "derivative", "حد", "limit",
]

_CHAT_KEYWORDS = [
    "اشرح", "explain", "ما هو", "what is", "كيف", "how", "لماذا", "why",
    "حدثني", "tell me", "معلومات", "information", "عرفني", "define",
]


def _count_keywords(text: str, keywords: list[str]) -> int:
    """Count keyword matches in text (case-insensitive)."""
    text_lower = text.lower()
    count = 0
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            count += 1
    return count


def classify_intent(
    user_text: str,
    *,
    explicit_feature: str | None = None,
    explicit_tier: str | None = None,
) -> IntentResult:
    """
    Classify user intent from text.
    
    If explicit_feature is provided, use it with confidence 1.0.
    If explicit_tier is provided, use it; otherwise default to 'default'.
    """
    # Explicit feature selection overrides classification
    if explicit_feature in ("chat", "presentation", "research", "question_solver"):
        return IntentResult(
            intent=explicit_feature,
            confidence=1.0,
            model_tier=explicit_tier or "default",
            requires_clarification=False,
            clarifying_question=None,
        )
    
    # Count keyword matches for each feature
    presentation_score = _count_keywords(user_text, _PRESENTATION_KEYWORDS)
    research_score = _count_keywords(user_text, _RESEARCH_KEYWORDS)
    question_score = _count_keywords(user_text, _QUESTION_SOLVER_KEYWORDS)
    chat_score = _count_keywords(user_text, _CHAT_KEYWORDS)
    
    scores = {
        "presentation": presentation_score,
        "research": research_score,
        "question_solver": question_score,
        "chat": chat_score,
    }
    
    # Find best match
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]
    
    # If no keywords matched, return unknown with low confidence
    if best_score == 0:
        return IntentResult(
            intent="unknown",
            confidence=0.3,
            model_tier=explicit_tier or "default",
            requires_clarification=True,
            clarifying_question=(
                "Would you like an explanation, a presentation, "
                "a research draft, or help solving a question?"
            ),
        )
    
    # Calculate confidence (normalized)
    total = sum(scores.values())
    confidence = best_score / total if total > 0 else 0.5
    
    # Determine if clarification needed (low confidence)
    requires_clarification = confidence < 0.6
    
    clarifying_question = None
    if requires_clarification:
        clarifying_question = (
            f"I detected '{best_intent}' with {confidence:.0%} confidence. "
            f"Would you like a {best_intent} or something else?"
        )
    
    return IntentResult(
        intent=best_intent,
        confidence=round(confidence, 2),
        model_tier=explicit_tier or "default",
        requires_clarification=requires_clarification,
        clarifying_question=clarifying_question,
    )


def is_ambiguous(result: IntentResult) -> bool:
    """Check if the intent result is ambiguous."""
    return result.requires_clarification or result.intent == "unknown"