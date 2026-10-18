"""
tests/unit/test_phase4_optimization.py
───────────────────────────────────────
Unit tests for Phase 4 backend optimizations:
- Database connection pool configuration
- Redis caching decorator and invalidation
- Rate limiting middleware dispatch logic
- AppException hierarchy and handlers
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse

from app.core.cache import cache_result, invalidate_cache
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from app.db.session import _make_engine
from app.middleware.rate_limit import RateLimitMiddleware


class TestDatabasePoolConfig:
    def test_postgres_pool_settings(self):
        with patch("app.db.session.get_settings") as mock_settings:
            mock_settings.return_value.async_database_url = "postgresql+asyncpg://user:pass@localhost:5432/spetser"
            mock_settings.return_value.is_development = False

            with patch("app.db.session.create_async_engine") as mock_create:
                _make_engine()
                mock_create.assert_called_once()
                _, kwargs = mock_create.call_args
                assert kwargs["pool_size"] == 20
                assert kwargs["max_overflow"] == 10
                assert kwargs["pool_timeout"] == 30
                assert kwargs["pool_recycle"] == 1800
                assert kwargs["pool_pre_ping"] is True


class TestCacheLayer:
    @pytest.mark.asyncio
    async def test_cache_result_and_fallback(self):
        call_count = 0

        @cache_result(ttl=60, prefix="test_calc")
        async def compute(x: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": x * 2}

        # Mock Redis get returning None, then cached value
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)

        with patch("app.core.cache.get_redis", return_value=mock_redis):
            res1 = await compute(5)
            assert res1 == {"result": 10}
            assert call_count == 1
            mock_redis.setex.assert_called_once()

            # Second call returns cached JSON string
            mock_redis.get = AsyncMock(return_value='{"result": 10}')
            res2 = await compute(5)
            assert res2 == {"result": 10}
            assert call_count == 1  # Function not re-invoked


class TestExceptionsHierarchy:
    def test_app_exception_properties(self):
        exc = NotFoundError("Item not found")
        assert exc.status_code == 404
        assert exc.code == "NOT_FOUND"
        assert exc.safe_message == "Item not found"

        auth_exc = AuthenticationError()
        assert auth_exc.status_code == 401
        assert auth_exc.code == "AUTH_ERROR"

        cred_exc = InsufficientCreditsError()
        assert cred_exc.status_code == 402
        assert cred_exc.code == "INSUFFICIENT_CREDITS"


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_bypass_health_endpoints(self):
        app = FastAPI()
        middleware = RateLimitMiddleware(app=app, max_requests=5, window_seconds=60)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/health/live"
        call_next = AsyncMock(return_value=PlainTextResponse("ok"))

        res = await middleware.dispatch(mock_request, call_next)
        assert res.status_code == 200
        call_next.assert_called_once_with(mock_request)
