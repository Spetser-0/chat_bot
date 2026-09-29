"""
app/services/providers/registry.py
────────────────────────────────────
Provider registry — resolves provider name to a concrete adapter instance.
Reads API keys from settings (server-side only).
Route handlers use this registry — never instantiate adapters directly.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.errors import ProviderUnsupportedModelError
from app.services.providers.base import AIProvider


@lru_cache(maxsize=1)
def _build_registry() -> dict[str, AIProvider]:
    """Build the provider registry once at startup."""
    settings = get_settings()
    registry: dict[str, AIProvider] = {}

    # Anthropic
    if settings.anthropic_api_key:
        try:
            from app.services.providers.anthropic_provider import AnthropicProvider
            registry["anthropic"] = AnthropicProvider(api_key=settings.anthropic_api_key)
        except Exception:
            pass  # Not installed or bad key — registered but will fail at use

    # Google Gemini
    if settings.google_gemini_api_key:
        try:
            from app.services.providers.gemini_provider import GeminiProvider
            registry["google_gemini"] = GeminiProvider(api_key=settings.google_gemini_api_key)
        except Exception:
            pass

    # Mock provider always available (used in tests)
    from app.services.providers.mock_provider import MockProvider
    registry["mock"] = MockProvider()

    return registry


def get_provider(provider_name: str) -> AIProvider:
    """
    Resolve a provider by name.
    Raises ProviderUnsupportedModelError if name is unknown.
    """
    registry = _build_registry()
    provider = registry.get(provider_name)
    if provider is None:
        raise ProviderUnsupportedModelError(
            f"Provider '{provider_name}' is not configured or available."
        )
    return provider


def list_provider_names() -> list[str]:
    return list(_build_registry().keys())
