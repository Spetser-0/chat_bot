"""
app/services/tool_registry.py
──────────────────────────────
Safe tool registry (Phase 4, Lesson 4.3→4.4).

Child analogy: the AI wears a costume (skill), and the costume has
pockets for tools. The registry is the school supply list: only these
pencil-boxes exist, only these are handed out today, and each box has
rules about what may go inside. Sharp tools (code execution, file
reading) are kept in a locked cupboard — listed, but disabled until the
sandbox room is built.

SECURITY: this module VALIDATES bindings only. It never executes tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.errors import ValidationError

_MAX_CONFIG_KEYS = 10
_MAX_CONFIG_STR_LEN = 500


@dataclass(frozen=True)
class ToolDescriptor:
    """One approved tool. `enabled=False` → reservable name, not bindable."""

    name: str
    description: str
    enabled: bool
    # config_key → allowed python types (instances checked with isinstance)
    config_schema: dict[str, type] = field(default_factory=dict)


# ── The whitelist ──────────────────────────────────────────────────────
TOOLS: dict[str, ToolDescriptor] = {
    "web_search": ToolDescriptor(
        name="web_search",
        description="Curated web search via a safe provider (server-side).",
        enabled=True,
        config_schema={"max_results": int, "region": str, "safe_search": bool},
    ),
    "calculator": ToolDescriptor(
        name="calculator",
        description="Arithmetic/expression evaluation in a pure sandbox.",
        enabled=True,
        config_schema={"precision": int},
    ),
    # Reserved — NOT bindable until their sandboxes exist:
    "code_executor": ToolDescriptor(
        name="code_executor",
        description="RESERVED: sandboxed code execution (not implemented).",
        enabled=False,
    ),
    "file_reader": ToolDescriptor(
        name="file_reader",
        description="RESERVED: reads user-uploaded files (not implemented).",
        enabled=False,
    ),
}


def get_tool(name: str) -> ToolDescriptor:
    """Return descriptor or raise ValidationError for unknown names."""
    tool = TOOLS.get(name)
    if tool is None:
        raise ValidationError(f"أداة غير معروفة: {name}")
    return tool


def list_tools(*, include_disabled: bool = False) -> list[ToolDescriptor]:
    """Descriptors for admin UI; disabled tools hidden unless requested."""
    return [t for t in TOOLS.values() if t.enabled or include_disabled]


def validate_tool_binding(name: str, config: dict[str, Any] | None) -> None:
    """Validate a SkillTool row BEFORE insert/update.

    - Unknown tool → ValidationError.
    - Disabled (reserved) tool → ValidationError (no premature binding).
    - Config: only declared keys, correct types, bounded size.
    """
    tool = get_tool(name)
    if not tool.enabled:
        raise ValidationError(f"الأداة '{name}' غير متاحة بعد (تتطلب صندوق حماية).")

    if config is None:
        return
    if not isinstance(config, dict):
        raise ValidationError("إعدادات الأداة يجب أن تكون كائنًا (JSON object).")
    if len(config) > _MAX_CONFIG_KEYS:
        raise ValidationError("إعدادات الأداة كثيرة جدًا.")
    for key, value in config.items():
        allowed = tool.config_schema.get(key)
        if allowed is None:
            raise ValidationError(f"مفتاح إعداد غير مسموح للأداة '{name}': {key}")
        # bool is a subclass of int — keep them distinct for clarity
        if allowed is int and isinstance(value, bool):
            raise ValidationError(f"قيمة غير صالحة للمفتاح '{key}'.")
        if not isinstance(value, allowed):
            raise ValidationError(f"قيمة غير صالحة للمفتاح '{key}'.")
        if isinstance(value, str) and len(value) > _MAX_CONFIG_STR_LEN:
            raise ValidationError(f"قيمة طويلة جدًا للمفتاح '{key}'.")
