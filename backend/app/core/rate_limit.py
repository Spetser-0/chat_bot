"""
app/core/rate_limit.py
──────────────────────
Shared rate-limit primitives used across auth, chat, payments, and admin.

Lesson 10.1 — Redis-ready store with graceful in-memory fallback.

Design:
- `RateLimitStore` is a tiny async interface: `hit(key, window_seconds) -> count`.
- `MemoryRateLimitStore` is the default (dev + tests, no external deps).
- `RedisRateLimitStore` is used when `RATE_LIMIT_BACKEND=redis` and Redis is reachable.
- On any Redis error the store degrades to memory (fail-open for availability)
  and logs a warning — never crash the request path because Redis is down.

Counters are fixed-window (simple, adequate for abuse control). Windows reset
after `window_seconds` from first hit in the window.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.errors import RateLimitError

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Store interface
# ──────────────────────────────────────────────────────────────────────────────

class RateLimitStore(ABC):
    """Async counter store keyed by arbitrary string."""

    @abstractmethod
    async def hit(self, key: str, window_seconds: int) -> int:
        """Increment the counter for `key` and return the new count."""

    @abstractmethod
    async def reset(self, key: str | None = None) -> None:
        """Clear counters (all keys if `key` is None)."""


class MemoryRateLimitStore(RateLimitStore):
    """In-process fixed-window counters. Suitable for single-instance dev/tests."""

    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        stored = self._counters.get(key)
        if stored is None or (now - stored[1]) >= window_seconds:
            self._counters[key] = (1, now)
            return 1
        count = stored[0] + 1
        self._counters[key] = (count, stored[1])
        return count

    async def reset(self, key: str | None = None) -> None:
        if key is None:
            self._counters.clear()
        else:
            self._counters.pop(key, None)


class RedisRateLimitStore(RateLimitStore):
    """Redis fixed-window counters (INCR + EXPIRE). Shared across instances."""

    def __init__(self, client: Any, fallback: MemoryRateLimitStore | None = None) -> None:
        self._client = client
        self._fallback = fallback or MemoryRateLimitStore()

    async def hit(self, key: str, window_seconds: int) -> int:
        try:
            count = await self._client.incr(key)
            if count == 1:
                await self._client.expire(key, window_seconds)
            return int(count)
        except Exception as exc:  # Redis down / network blip — fail-open to memory
            logger.warning("redis_rate_limit_fallback", error_type=type(exc).__name__)
            return await self._fallback.hit(key, window_seconds)

    async def reset(self, key: str | None = None) -> None:
        try:
            if key is None:
                await self._client.flushdb()
            else:
                await self._client.delete(key)
        except Exception as exc:
            logger.warning("redis_rate_limit_reset_fallback", error_type=type(exc).__name__)
            await self._fallback.reset(key)


# ──────────────────────────────────────────────────────────────────────────────
# Factory + shared singleton
# ──────────────────────────────────────────────────────────────────────────────

_store: RateLimitStore | None = None


async def _build_redis_store() -> RedisRateLimitStore | None:
    """Create a RedisRateLimitStore if redis is importable and reachable."""
    settings = get_settings()
    try:
        import redis.asyncio as aioredis
    except ImportError:
        logger.warning("redis_package_missing", hint="pip install redis")
        return None
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        logger.info("rate_limit_store_ready", backend="redis")
        return RedisRateLimitStore(client)
    except Exception as exc:
        logger.warning("redis_unavailable_fallback_memory", error_type=type(exc).__name__)
        return None


def get_rate_limit_store() -> RateLimitStore:
    """Return the process-wide rate-limit store (lazy singleton).

    Backend is resolved on first use from settings:
    - RATE_LIMIT_BACKEND=memory (default) → MemoryRateLimitStore
    - RATE_LIMIT_BACKEND=redis → RedisRateLimitStore, or memory if Redis is down
    """
    global _store
    if _store is not None:
        return _store

    settings = get_settings()
    if settings.rate_limit_backend == "redis":
        # Sync path: try to construct without awaiting ping here; hit() will
        # fall back if Redis is unreachable. For simplicity we build memory and
        # upgrade asynchronously via init_redis_store() in lifespan when needed.
        # Direct construction below uses the URL only — connection errors are
        # handled inside hit().
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            _store = RedisRateLimitStore(client)
            logger.info("rate_limit_store_ready", backend="redis")
            return _store
        except ImportError:
            logger.warning("redis_package_missing", hint="pip install redis")
        except Exception as exc:
            logger.warning("redis_store_init_failed", error_type=type(exc).__name__)

    _store = MemoryRateLimitStore()
    logger.info("rate_limit_store_ready", backend="memory")
    return _store


async def init_redis_store() -> None:
    """Lifespan hook: verify Redis connectivity and swap in RedisRateLimitStore if healthy."""
    global _store
    settings = get_settings()
    if settings.rate_limit_backend != "redis":
        return
    store = await _build_redis_store()
    if store is not None:
        _store = store


async def close_rate_limit_store() -> None:
    """Lifespan hook: close Redis client if open."""
    global _store
    if isinstance(_store, RedisRateLimitStore):
        client = getattr(_store, "_client", None)
        if client is not None:
            try:
                await client.aclose()
            except Exception:
                pass
    _store = None


def reset_rate_limit_store_for_tests() -> None:
    """Reset the singleton (used by test fixtures)."""
    global _store
    _store = None


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

async def enforce_rate_limit(
    store: RateLimitStore,
    key: str,
    limit: int,
    window_seconds: int,
    safe_message: str | None = None,
) -> None:
    """Raise RateLimitError if the key exceeds `limit` within `window_seconds`."""
    count = await store.hit(key, window_seconds)
    if count > limit:
        raise RateLimitError(safe_message) if safe_message else RateLimitError()


def rate_limit_key_for_user(user_id: str, scope: str) -> str:
    """Stable key for per-user limits, e.g. rate:chat:u:<uuid>."""
    return f"rate:{scope}:u:{user_id}"


def rate_limit_key_for_ip(ip: str, scope: str) -> str:
    """Stable key for per-IP limits (auth/webhooks), e.g. rate:auth:ip:1.2.3.4."""
    return f"rate:{scope}:ip:{ip}"
