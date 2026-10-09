"""
app/core/validation.py
──────────────────────
Shared input-sanitization helpers (Phase 10, Lesson 10.3).

Rules:
- Strip C0/C1 control characters except \n and \t (they are meaningful in text).
- Strip the Unicode NUL character and other invisible format chars that can
  hide prompt-injection payloads or break logs.
- Collapse leading/trailing whitespace (callers may strip again).
- Do NOT change content beyond control-char removal — Arabic, emoji, etc. stay.
"""
from __future__ import annotations

import re

# C0 controls (0x00–0x1F) excluding \n (0x0A) and \t (0x09),
# plus DEL (0x7F) and C1 controls (0x80–0x9F).
_CONTROL_CHARS = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]"
)


def strip_control_chars(value: str) -> str:
    """Remove control characters that should never appear in user text."""
    return _CONTROL_CHARS.sub("", value)


def sanitize_user_text(value: str, *, max_length: int | None = None) -> str:
    """Sanitize free-form user text: strip control chars, collapse edges, cap length."""
    cleaned = strip_control_chars(value).strip()
    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned
