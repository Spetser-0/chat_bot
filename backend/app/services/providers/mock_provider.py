"""
app/services/providers/mock_provider.py
─────────────────────────────────────────
Deterministic mock provider for testing.
Returns configurable fixed responses without hitting any external API.
"""
from __future__ import annotations

import json
import time

from app.services.providers.base import AIProvider, ProviderResponse


class MockProvider:
    """
    Deterministic provider for unit and integration tests.
    Configure via constructor arguments to control response shape.
    """

    def __init__(
        self,
        *,
        fixed_text: str = "Mock response text.",
        fixed_structured: dict | None = None,
        input_tokens: int = 100,
        output_tokens: int = 200,
        latency_ms: float = 50.0,
        raise_on_generate: Exception | None = None,
        health: bool = True,
    ) -> None:
        self._fixed_text = fixed_text
        self._fixed_structured = fixed_structured
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._latency_ms = latency_ms
        self._raise = raise_on_generate
        self._health = health
        self.call_count = 0
        self.last_call_kwargs: dict | None = None

    @property
    def name(self) -> str:
        return "mock"

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
        self.call_count += 1
        self.last_call_kwargs = {
            "messages": messages,
            "system_prompt": system_prompt,
            "model": model,
            "response_schema": response_schema,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if self._raise is not None:
            raise self._raise

        return ProviderResponse(
            provider_name=self.name,
            model_name=model,
            raw_text=self._fixed_text if self._fixed_structured is None else None,
            structured_output=self._fixed_structured,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            request_id="mock-request-id",
            finish_reason="stop",
            latency_ms=self._latency_ms,
        )

    async def health_check(self) -> bool:
        return self._health
