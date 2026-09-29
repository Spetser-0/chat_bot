"""
app/services/providers/gemini_provider.py
──────────────────────────────────────────
Adapter for Google Gemini models.
Uses google-generativeai SDK and normalizes to ProviderResponse.
"""
from __future__ import annotations

import json
import time

from app.core.errors import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderError,
)
from app.services.providers.base import ProviderResponse

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False


class GeminiProvider:
    """
    Adapter for Google Gemini provider.
    API key is passed at construction — never from client requests.
    """

    def __init__(self, api_key: str, default_max_tokens: int = 8192) -> None:
        if not _GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed")
        if not api_key:
            raise ProviderAuthError("Google Gemini API key is not configured.")
        genai.configure(api_key=api_key)
        self._api_key = api_key
        self._default_max_tokens = default_max_tokens

    @property
    def name(self) -> str:
        return "google_gemini"

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
        import asyncio

        start = time.monotonic()

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens or self._default_max_tokens,
            temperature=temperature,
        )

        if response_schema:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens or self._default_max_tokens,
                temperature=temperature,
                response_mime_type="application/json",
            )

        client = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=generation_config,
        )

        # Convert messages to Gemini format
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        last_message = messages[-1]["content"] if messages else ""

        try:
            chat = client.start_chat(history=history)
            # Run blocking SDK call in thread pool
            response = await asyncio.to_thread(
                chat.send_message, last_message
            )
        except Exception as exc:
            name = type(exc).__name__
            msg_lower = str(exc).lower()
            if "api_key" in msg_lower or "credentials" in msg_lower or "permission" in msg_lower:
                raise ProviderAuthError() from exc
            if "quota" in msg_lower or "rate" in msg_lower or "429" in msg_lower:
                raise ProviderRateLimitError() from exc
            if "timeout" in msg_lower or "deadline" in msg_lower:
                raise ProviderTimeoutError() from exc
            raise ProviderError(safe_message=str(exc)[:100]) from exc

        latency_ms = (time.monotonic() - start) * 1000

        raw_text = response.text
        structured_output = None

        if response_schema and raw_text:
            try:
                structured_output = json.loads(raw_text)
                raw_text = None
            except json.JSONDecodeError as exc:
                raise ProviderInvalidResponseError(
                    "Gemini returned invalid JSON despite json response mode."
                ) from exc

        usage = response.usage_metadata
        return ProviderResponse(
            provider_name=self.name,
            model_name=model,
            raw_text=raw_text,
            structured_output=structured_output,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            request_id=None,
            finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        """Quick check that API key is valid."""
        import asyncio
        try:
            client = genai.GenerativeModel("gemini-1.5-flash")
            await asyncio.to_thread(client.generate_content, "ping")
            return True
        except Exception:
            return False
