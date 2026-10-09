"""
tests/unit/test_rate_limit.py
─────────────────────────────
Lesson 10.1 — RateLimitStore (memory + redis fallback) and enforce helper.
"""
from __future__ import annotations

import pytest

from app.core.errors import RateLimitError
from app.core.rate_limit import (
    MemoryRateLimitStore,
    RedisRateLimitStore,
    enforce_rate_limit,
    get_rate_limit_store,
    rate_limit_key_for_ip,
    rate_limit_key_for_user,
    reset_rate_limit_store_for_tests,
)


class TestMemoryRateLimitStore:
    async def test_first_hit_returns_one(self):
        store = MemoryRateLimitStore()
        assert await store.hit("k", 60) == 1

    async def test_increments_within_window(self):
        store = MemoryRateLimitStore()
        await store.hit("k", 60)
        assert await store.hit("k", 60) == 2
        assert await store.hit("k", 60) == 3

    async def test_separate_keys_independent(self):
        store = MemoryRateLimitStore()
        await store.hit("a", 60)
        await store.hit("a", 60)
        assert await store.hit("b", 60) == 1

    async def test_reset_single_key(self):
        store = MemoryRateLimitStore()
        await store.hit("k", 60)
        await store.reset("k")
        assert await store.hit("k", 60) == 1

    async def test_reset_all(self):
        store = MemoryRateLimitStore()
        await store.hit("a", 60)
        await store.hit("b", 60)
        await store.reset()
        assert await store.hit("a", 60) == 1
        assert await store.hit("b", 60) == 1


class _FakeRedis:
    """Minimal async Redis stub for hit/reset tests."""

    def __init__(self, fail: bool = False) -> None:
        self.data: dict[str, int] = {}
        self.ttl: dict[str, int] = {}
        self.fail = fail

    async def incr(self, key: str) -> int:
        if self.fail:
            raise ConnectionError("redis down")
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttl[key] = seconds
        return True

    async def delete(self, key: str) -> int:
        if self.fail:
            raise ConnectionError("redis down")
        return 1 if self.data.pop(key, None) is not None else 0

    async def flushdb(self) -> bool:
        if self.fail:
            raise ConnectionError("redis down")
        self.data.clear()
        return True


class TestRedisRateLimitStore:
    async def test_hit_increments(self):
        client = _FakeRedis()
        store = RedisRateLimitStore(client)
        assert await store.hit("k", 60) == 1
        assert await store.hit("k", 60) == 2

    async def test_first_hit_sets_ttl(self):
        client = _FakeRedis()
        store = RedisRateLimitStore(client)
        await store.hit("k", 30)
        assert client.ttl["k"] == 30

    async def test_fallback_to_memory_on_error(self):
        client = _FakeRedis(fail=True)
        store = RedisRateLimitStore(client)
        # Redis raises → falls back to memory counter
        assert await store.hit("k", 60) == 1
        assert await store.hit("k", 60) == 2

    async def test_reset_falls_back_on_error(self):
        client = _FakeRedis(fail=True)
        store = RedisRateLimitStore(client)
        await store.hit("k", 60)
        await store.reset("k")  # must not raise
        await store.reset()


class TestEnforceRateLimit:
    async def test_allows_within_limit(self):
        store = MemoryRateLimitStore()
        for _ in range(5):
            await enforce_rate_limit(store, "k", limit=5, window_seconds=60)

    async def test_blocks_over_limit(self):
        store = MemoryRateLimitStore()
        for _ in range(5):
            await enforce_rate_limit(store, "k", limit=5, window_seconds=60)
        with pytest.raises(RateLimitError):
            await enforce_rate_limit(store, "k", limit=5, window_seconds=60)

    async def test_custom_safe_message(self):
        store = MemoryRateLimitStore()
        with pytest.raises(RateLimitError) as exc:
            await enforce_rate_limit(
                store, "k", limit=0, window_seconds=60, safe_message="حاول لاحقاً."
            )
        assert exc.value.safe_message == "حاول لاحقاً."


class TestKeysAndFactory:
    def test_user_key(self):
        assert rate_limit_key_for_user("abc", "chat") == "rate:chat:u:abc"

    def test_ip_key(self):
        assert rate_limit_key_for_ip("1.2.3.4", "auth") == "rate:auth:ip:1.2.3.4"

    def test_get_store_returns_singleton(self):
        reset_rate_limit_store_for_tests()
        s1 = get_rate_limit_store()
        s2 = get_rate_limit_store()
        assert s1 is s2
        assert isinstance(s1, MemoryRateLimitStore)  # default backend is memory in tests
