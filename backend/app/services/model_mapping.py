"""
app/services/model_mapping.py
─────────────────────────────
Map frontend model strength (flash / think / pro) to backend model configurations.
"""
from __future__ import annotations

from typing import Any, Literal

def map_strength_to_model(strength: Literal["flash", "think", "pro"] | str) -> dict[str, Any]:
    """
    Map frontend model strength to backend provider/model configuration.
    
    This allows the frontend to send abstract strength levels while the
    backend decides which actual model to use based on cost/availability.
    """
    mapping: dict[str, dict[str, Any]] = {
        "flash": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2048,
        },
        "think": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "pro": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "temperature": 0.5,
            "max_tokens": 8192,
        },
    }
    return mapping.get(str(strength), mapping["think"])
