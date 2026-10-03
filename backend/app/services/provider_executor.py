"""
app/services/provider_executor.py
──────────────────────────────────
Provider execution with bounded retries and error mapping.

Handles:
- Bounded retries with exponential backoff for recoverable errors
- Safe error mapping without leaking secrets
- Provider health status abstraction
- Latency tracking
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING

from app.core.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnsupportedModelError,
    SpetserError,
)
from app.services.providers.base import AIProvider, ProviderResponse
from app.services.routing import ResolvedModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ──────────────────────────────────────────────────────────────────────────────
# Error Classification
# ──────────────────────────────────────────────────────────────────────────────

class RecoverableProviderError(Exception):
    """Base for provider errors that are safe to retry."""


class NonRecoverableProviderError(Exception):
    """Base for provider errors that should NOT be retried."""


def classify_provider_error(exc: Exception) -> tuple[type[Exception], bool]:
    """
    Classify a provider exception as recoverable or not.
    
    Returns: (exception_class, is_recoverable)
    """
    # Authentication errors are NEVER retried
    if isinstance(exc, ProviderAuthError):
        return (NonRecoverableProviderError, False)
    
    # Unsupported model is not retryable
    if isinstance(exc, ProviderUnsupportedModelError):
        return (NonRecoverableProviderError, False)
    
    # Rate limits and timeouts ARE recoverable
    if isinstance(exc, (ProviderRateLimitError, ProviderTimeoutError)):
        return (RecoverableProviderError, True)
    
    # Invalid response might be recoverable (try different model)
    if isinstance(exc, ProviderInvalidResponseError):
        return (RecoverableProviderError, True)
    
    # Generic provider error - check if it's a connection/temporary issue
    if isinstance(exc, ProviderError):
        msg = str(exc).lower()
        if any(kw in msg for kw in ("connection", "timeout", "temporary", "unavailable", "503", "502")):
            return (RecoverableProviderError, True)
        return (NonRecoverableProviderError, False)
    
    # Unknown exceptions - treat as potentially recoverable but log
    return (RecoverableProviderError, True)


# ──────────────────────────────────────────────────────────────────────────────
# Retry Policy
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    jitter: float = 0.1  # ±10% jitter


DEFAULT_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay_seconds=1.0,
    max_delay_seconds=30.0,
)


def calculate_backoff(attempt: int, policy: RetryPolicy) -> float:
    """Calculate exponential backoff with jitter."""
    import random
    delay = min(
        policy.base_delay_seconds * (policy.exponential_base ** attempt),
        policy.max_delay_seconds,
    )
    # Add jitter
    jitter_range = delay * policy.jitter
    return delay + random.uniform(-jitter_range, jitter_range)


# ──────────────────────────────────────────────────────────────────────────────
# Execution Result
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionResult:
    """Result of provider execution with fallback tracking."""
    response: ProviderResponse
    model_used: ResolvedModel
    attempt: int              # 1-indexed attempt number (1 = primary, 2 = first fallback, etc.)
    fallback_used: bool
    total_latency_ms: float


@dataclass(frozen=True)
class ExecutionFailure:
    """Record of a failed provider execution."""
    model: ResolvedModel
    error: Exception
    attempt: int
    is_recoverable: bool


# ──────────────────────────────────────────────────────────────────────────────
# Provider Executor
# ──────────────────────────────────────────────────────────────────────────────

class ProviderExecutor:
    """
    Executes provider calls with bounded retries and fallback support.
    
    Usage:
        executor = ProviderExecutor(
            models=[primary, *fallbacks],
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        result = await executor.execute(
            messages=...,
            system_prompt=...,
            response_schema=...,
        )
    """
    
    def __init__(
        self,
        models: list[ResolvedModel],
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ):
        if not models:
            raise ValueError("At least one model must be provided")
        self._models = models
        self._policy = retry_policy
        self._logger = logging.getLogger("spetser.provider_executor")
    
    async def execute(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str,
        response_schema: dict | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ExecutionResult:
        """
        Execute with retries and fallbacks.
        
        Returns ExecutionResult on success.
        Raises the last non-recoverable error or final ProviderError on total failure.
        """
        last_error: Exception | None = None
        total_latency = 0.0
        
        for model_index, model in enumerate(self._models):
            attempt = 1
            max_attempts = self._policy.max_attempts if model_index == 0 else 1
            
            while attempt <= max_attempts:
                provider = await get_provider_instance(model.provider_key)
                start = time.monotonic()
                
                try:
                    response = await provider.generate(
                        messages=messages,
                        system_prompt=system_prompt,
                        model=model.model_name,
                        response_schema=response_schema,
                        max_tokens=max_tokens or model.max_tokens,
                        temperature=temperature if temperature is not None else model.temperature,
                    )
                    
                    latency_ms = (time.monotonic() - start) * 1000
                    total_latency += latency_ms
                    
                    self._logger.info(
                        "Provider call succeeded provider=%s model=%s attempt=%d model_index=%d latency_ms=%.2f",
                        model.provider_key, model.model_name, attempt, model_index, latency_ms
                    )
                    
                    return ExecutionResult(
                        response=response,
                        model_used=model,
                        attempt=attempt,
                        fallback_used=model_index > 0,
                        total_latency_ms=total_latency,
                    )
                    
                except Exception as exc:
                    latency_ms = (time.monotonic() - start) * 1000
                    total_latency += latency_ms
                    
                    _, is_recoverable = classify_provider_error(exc)
                    
                    self._logger.warning(
                        "Provider call failed provider=%s model=%s attempt=%d model_index=%d error_type=%s is_recoverable=%s latency_ms=%.2f",
                        model.provider_key, model.model_name, attempt, model_index,
                        type(exc).__name__, is_recoverable, latency_ms
                    )
                    
                    last_error = exc
                    
                    if not is_recoverable:
                        # Non-recoverable error - don't retry this model, try fallback
                        break
                    
                    if attempt < max_attempts:
                        delay = calculate_backoff(attempt, self._policy)
                        self._logger.info(
                            "Retrying after delay delay_seconds=%.2f provider=%s model=%s",
                            delay, model.provider_key, model.model_name
                        )
                        await asyncio.sleep(delay)
                        attempt += 1
                    else:
                        # Exhausted retries for this model
                        break
            
            # If we get here, this model failed (exhausted retries or non-recoverable)
            # Continue to next fallback model
            continue
        
        # All models exhausted
        self._logger.error(
            "All provider models exhausted models_tried=%d last_error_type=%s",
            len(self._models), type(last_error).__name__ if last_error else None
        )
        
        # Re-raise the last error as a ProviderError
        if last_error:
            if isinstance(last_error, SpetserError):
                raise last_error
            raise ProviderError(str(last_error)[:100]) from last_error
        
        raise ProviderError("All provider models failed without a specific error.")


async def get_provider_instance(provider_key: str) -> AIProvider:
    """Get provider adapter instance."""
    from app.services.providers.registry import get_provider
    return get_provider(provider_key)


# ──────────────────────────────────────────────────────────────────────────────
# Provider Health Service
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProviderHealth:
    """Health status for a single provider."""
    provider_key: str
    display_name: str
    healthy: bool
    last_check_at: str | None = None
    last_error: str | None = None


async def check_provider_health(
    db: AsyncSession,
) -> list[ProviderHealth]:
    """
    Check health of all enabled providers.
    Updates DB with last check time and error.
    """
    from datetime import datetime

    from sqlalchemy import select

    from app.models.provider import ModelProvider
    
    result = await db.execute(
        select(ModelProvider).where(ModelProvider.enabled.is_(True))
    )
    providers = result.scalars().all()
    
    health_results = []
    
    for provider in providers:
        try:
            adapter = await get_provider_instance(provider.provider_key)
            healthy = await adapter.health_check()
            
            provider.health_status = "healthy" if healthy else "unhealthy"
            provider.last_health_check_at = datetime.now(UTC)
            if not healthy:
                provider.last_error_message = "Health check failed"
            else:
                provider.last_error_message = None
            
            health_results.append(ProviderHealth(
                provider_key=provider.provider_key,
                display_name=provider.display_name,
                healthy=healthy,
                last_check_at=provider.last_health_check_at.isoformat() if provider.last_health_check_at else None,
                last_error=provider.last_error_message,
            ))
            
        except Exception as exc:
            provider.health_status = "error"
            provider.last_health_check_at = datetime.now(UTC)
            provider.last_error_message = str(exc)[:200]
            
            health_results.append(ProviderHealth(
                provider_key=provider.provider_key,
                display_name=provider.display_name,
                healthy=False,
                last_check_at=provider.last_health_check_at.isoformat() if provider.last_health_check_at else None,
                last_error=str(exc)[:200],
            ))
    
    await db.commit()
    return health_results