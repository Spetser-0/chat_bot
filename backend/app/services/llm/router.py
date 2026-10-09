"""
app/services/llm/router.py
──────────────────────────
Multi-provider LLM router (Phase 3, Lessons 3.4–3.7).

Responsibilities:
- Select the right AIProvider row from the DB (skill preference →
  fallback → priority-weighted active pool).
- Call the model through LiteLLM with the provider's decrypted key.
- Fail over to the next candidate on timeout / rate-limit / 5xx,
  respecting per-provider max_retries and timeout_seconds.
- Track per-call cost from provider cost_input/output_per_1k.

Design decisions:
- LiteLLM (`acompletion`) normalizes OpenAI/Anthropic/Gemini/etc. so we
  write ONE call path. Provider slugs map to LiteLLM model strings via
  provider_metadata["litellm_model"] (falls back to model_name).
- Never log decrypted keys — structlog redaction covers message bodies,
  and keys are only touched inside `_call_with_provider`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import litellm
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProviderError, RoutingError
from app.models.ai_provider import AIProvider
from app.models.skill import Skill
from app.services.provider_service import ProviderService

logger = structlog.get_logger(__name__)

# Transient errors worth failing over on. Everything else raises at once.
_RETRYABLE = (
    litellm.Timeout,
    litellm.RateLimitError,
    litellm.ServiceUnavailableError,
    litellm.APIConnectionError,
)


@dataclass(frozen=True)
class StreamEvent:
    """One SSE-compatible event emitted during a streamed completion.

    Event types:
    - "start":  stream opened; carries provider_slug and model_name.
    - "chunk":  carries text delta.
    - "done":   final event; carries usage + cost (tokens may be 0 if the
                provider does not stream usage).
    - "error":  safe terminal error (code + message), never a stack trace.
    """

    type: str
    data: dict[str, Any]

    def to_sse(self) -> str:
        """Render as SSE frame: `event: <type>\\ndata: <json>\\n\\n`."""
        import json

        return f"event: {self.type}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


@dataclass(frozen=True)
class RoutingResult:
    """Normalized output of a routed completion call."""

    text: str
    provider_slug: str
    model_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: float
    attempts: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMRouter:
    """Route completion calls across DB-configured providers."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._providers = ProviderService(db)

    # ── Public API ─────────────────────────────────────────────────────
    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        capability: str = "chat",
        skill: Skill | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> RoutingResult:
        """Route a completion through the best available provider.

        Selection order (Lesson 3.5):
        1. skill.preferred_provider  2. skill.fallback_provider
        3. Active pool ordered by priority_weight.
        Failover (Lesson 3.6): retry transient errors, then next candidate.
        """
        candidates = await self._select_candidates(skill)
        if not candidates:
            raise RoutingError("No active AI providers configured")

        attempts: list[str] = []
        last_error: Exception | None = None
        for provider in candidates:
            try:
                return await self._call_with_provider(
                    provider,
                    capability=capability,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    attempts=attempts,
                )
            except _RETRYABLE as exc:
                attempts.append(f"{provider.slug}:{type(exc).__name__}")
                last_error = exc
                logger.warning(
                    "provider_failed_over",
                    provider=provider.slug,
                    error=type(exc).__name__,
                )
                continue

        raise ProviderError(
            f"All providers failed. Attempts: {attempts}"
        ) from last_error

    # ── Streaming (Lesson 3.8) ─────────────────────────────────────────
    async def stream_complete(
        self,
        *,
        messages: list[dict[str, str]],
        capability: str = "streaming",
        skill: Skill | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """Async generator of StreamEvent for streaming completions.

        Failover occurs BEFORE the first token (a failing provider is
        swapped during the retry loop below). Once tokens flow, a failure
        yields a terminal "error" event instead of raising mid-stream —
        partial text is kept by the client.
        """
        candidates = await self._select_candidates(skill)
        if not candidates:
            yield StreamEvent("error", {
                "code": "provider_unavailable",
                "message": "No active AI providers configured",
            })
            return

        last_error: Exception | None = None
        for provider in candidates:
            try:
                await self._providers.validate_for_call(provider, capability)
                api_key = await self._providers.decrypted_key(provider)
            except ProviderError as exc:
                last_error = exc
                continue

            model = self._litellm_model(provider)
            start = time.perf_counter()
            stream = None
            for attempt in range(provider.max_retries):
                try:
                    stream = await litellm.acompletion(
                        model=model,
                        messages=messages,
                        api_key=api_key,
                        timeout=provider.timeout_seconds,
                        max_retries=0,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=True,
                        stream_options={"include_usage": True},
                    )
                    break  # stream opened — leave retry loop
                except _RETRYABLE as exc:
                    last_error = exc
                    if attempt == provider.max_retries - 1:
                        stream = None
                        break
                    continue
                except Exception as exc:  # non-retryable (auth, bad request)
                    yield StreamEvent("error", {
                        "code": "provider_unavailable",
                        "message": f"Provider '{provider.slug}' rejected the request",
                    })
                    logger.warning("stream_open_failed",
                                   provider=provider.slug,
                                   error=type(exc).__name__)
                    return

            if stream is None:
                logger.warning("provider_failed_over",
                               provider=provider.slug, streaming=True)
                continue  # try next candidate

            # Stream is open — emit events. Mid-stream errors are terminal.
            yield StreamEvent("start", {
                "provider_slug": provider.slug,
                "model_name": provider.model_name,
            })
            input_tokens = output_tokens = 0
            try:
                async for part in stream:
                    choice = part.choices[0] if part.choices else None
                    delta = getattr(choice, "delta", None) if choice else None
                    text = getattr(delta, "content", None) if delta else None
                    if text:
                        yield StreamEvent("chunk", {"text": text})
                    usage = getattr(part, "usage", None)
                    if usage:
                        input_tokens = usage.prompt_tokens or input_tokens
                        output_tokens = usage.completion_tokens or output_tokens
            except Exception as exc:
                logger.warning("stream_interrupted",
                               provider=provider.slug,
                               error=type(exc).__name__)
                yield StreamEvent("error", {
                    "code": "provider_unavailable",
                    "message": "Stream interrupted by provider",
                })
                return

            latency = (time.perf_counter() - start) * 1000
            yield StreamEvent("done", {
                "provider_slug": provider.slug,
                "model_name": provider.model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": str(self._compute_cost(provider, input_tokens,
                                                   output_tokens)),
                "latency_ms": round(latency, 2),
            })
            return

        yield StreamEvent("error", {
            "code": "provider_unavailable",
            "message": "All providers failed",
        })
        logger.error("stream_all_providers_failed", error=str(last_error))

    # ── Selection (Lesson 3.5) ─────────────────────────────────────────
    async def _select_candidates(self, skill: Skill | None) -> list[AIProvider]:
        pool = await self._providers.list_active()
        ordered: list[AIProvider] = []
        if skill is not None:
            for pid in (skill.preferred_provider_id, skill.fallback_provider_id):
                if pid is None:
                    continue
                match = next((p for p in pool if p.id == pid), None)
                if match is not None and match not in ordered:
                    ordered.append(match)
        ordered.extend(p for p in pool if p not in ordered)
        return ordered

    # ── Call + failover + cost (Lessons 3.6–3.7) ───────────────────────
    async def _call_with_provider(
        self,
        provider: AIProvider,
        *,
        capability: str,
        messages: list[dict[str, str]],
        max_tokens: int | None,
        temperature: float | None,
        attempts: list[str],
    ) -> RoutingResult:
        await self._providers.validate_for_call(provider, capability)
        api_key = await self._providers.decrypted_key(provider)
        model = self._litellm_model(provider)

        for attempt in range(provider.max_retries):
            start = time.perf_counter()
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    api_key=api_key,
                    timeout=provider.timeout_seconds,
                    max_retries=0,  # failover handled here, not in litellm
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except _RETRYABLE:
                if attempt == provider.max_retries - 1:
                    raise
                continue

            latency = (time.perf_counter() - start) * 1000
            usage = response.usage
            cost = self._compute_cost(
                provider, usage.prompt_tokens, usage.completion_tokens
            )
            return RoutingResult(
                text=response.choices[0].message.content or "",
                provider_slug=provider.slug,
                model_name=provider.model_name,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost_usd=cost,
                latency_ms=latency,
                attempts=attempts + [provider.slug],
            )

        raise ProviderError(f"Provider '{provider.slug}' exhausted retries")

    @staticmethod
    def _litellm_model(provider: AIProvider) -> str:
        metadata: dict[str, Any] = provider.provider_metadata or {}
        return metadata.get("litellm_model", provider.model_name)

    @staticmethod
    def _compute_cost(
        provider: AIProvider, input_tokens: int, output_tokens: int
    ) -> Decimal:
        cost = (
            Decimal(input_tokens) / 1000 * provider.cost_input_per_1k
            + Decimal(output_tokens) / 1000 * provider.cost_output_per_1k
        )
        return cost.quantize(Decimal("0.000001"))
