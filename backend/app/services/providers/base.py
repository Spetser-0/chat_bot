"""
app/services/providers/base.py
────────────────────────────────
Provider protocol and normalized response shape.
All concrete provider adapters must conform to this interface.
Route handlers MUST NOT import provider adapters directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderResponse:
    """
    Normalized output from any AI provider.
    All fields must be populated by each adapter.
    """
    provider_name: str
    model_name: str
    # Either raw_text or structured_output will be set, not both
    raw_text: str | None = None
    structured_output: Any = None
    input_tokens: int = 0
    output_tokens: int = 0
    request_id: str | None = None
    finish_reason: str | None = None
    latency_ms: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@runtime_checkable
class AIProvider(Protocol):
    """
    Abstract interface every provider adapter must implement.
    Never import a concrete adapter in route handlers or feature services.
    """

    @property
    def name(self) -> str:
        """Stable provider key, e.g. 'anthropic', 'google_gemini'."""
        ...

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str,
        model: str,
        response_schema: dict | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ProviderResponse:
        """
        Generate a completion.
        Raises a subclass of SpetserError on any failure.
        """
        ...

    async def health_check(self) -> bool:
        """Return True if the provider is reachable and authenticated."""
        ...
