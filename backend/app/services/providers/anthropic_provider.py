"""
app/services/providers/anthropic_provider.py
─────────────────────────────────────────────
Adapter for Anthropic Claude models.
Normalizes all output to ProviderResponse.
Maps Anthropic errors to typed SpetserErrors.
"""
from __future__ import annotations

import json
import time

import httpx

from app.core.errors import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderError,
)
from app.services.providers.base import AIProvider, ProviderResponse

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


class AnthropicProvider:
    """
    Adapter for Anthropic / Claude provider.
    API key is passed at construction — never from client requests.
    """

    def __init__(self, api_key: str, default_max_tokens: int = 8192) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed")
        if not api_key:
            raise ProviderAuthError("Anthropic API key is not configured.")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._default_max_tokens = default_max_tokens

    @property
    def name(self) -> str:
        return "anthropic"

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
        start = time.monotonic()
        kwargs: dict = {
            "model": model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": max_tokens or self._default_max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        # Request structured JSON output when schema is provided
        if response_schema:
            kwargs["tools"] = [
                {
                    "name": "structured_output",
                    "description": "Return data conforming to the provided schema.",
                    "input_schema": response_schema,
                }
            ]
            kwargs["tool_choice"] = {"type": "tool", "name": "structured_output"}

        try:
            response = await self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise ProviderAuthError() from e
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError() from e
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError() from e
        except anthropic.APIError as e:
            raise ProviderError(safe_message=str(e)[:100]) from e

        latency_ms = (time.monotonic() - start) * 1000

        # Parse structured output from tool use
        structured_output = None
        raw_text = None
        finish_reason = response.stop_reason

        if response_schema and response.stop_reason == "tool_use":
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    structured_output = block.input
                    break
            if structured_output is None:
                raise ProviderInvalidResponseError(
                    "Expected tool_use block in Anthropic response but found none."
                )
        else:
            text_parts = [
                block.text
                for block in response.content
                if hasattr(block, "text")
            ]
            raw_text = "\n".join(text_parts)

        return ProviderResponse(
            provider_name=self.name,
            model_name=response.model,
            raw_text=raw_text,
            structured_output=structured_output,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_id=response.id,
            finish_reason=str(finish_reason),
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        """Minimal API call to verify connectivity and auth."""
        try:
            await self._client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except anthropic.AuthenticationError:
            return False
        except Exception:
            return False
