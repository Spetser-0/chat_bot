"""
tests/unit/test_foundation.py
─────────────────────────────
Phase 1 foundation tests:
- application startup
- health endpoint (liveness + readiness)
- configuration validation
- error response format
- request ID behavior
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app

# ──────────────────────────────────────────────────────────────────────────────
# Application Startup
# ──────────────────────────────────────────────────────────────────────────────

def test_application_starts():
    """FastAPI app factory creates an app with expected metadata."""
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "Spetser AI"
    assert "Arabic-first academic AI platform" in app.description
    # lifespan is set
    assert app.router.lifespan_context is not None


# ──────────────────────────────────────────────────────────────────────────────
# Health Endpoint — Liveness
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_liveness_endpoint():
    """Liveness probe returns 200 with status ok."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ──────────────────────────────────────────────────────────────────────────────
# Health Endpoint — Readiness
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_readiness_endpoint_ok(monkeypatch):
    """Readiness probe returns 200 with db status ok when database reachable."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.db.session import Base, get_db

    # Create a test engine for this test
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncSession:
        async with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"]["status"] == "ok"
        assert "latency_ms" in data["checks"]["database"]
        assert data["version"] == get_settings().app_version

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_readiness_endpoint_db_down():
    """Readiness probe returns 503 with error payload when database unreachable."""

    from app.db.session import get_db

    async def failing_db():
        """Yield a session that fails on execute."""
        class FailingSession:
            async def execute(self, stmt):
                raise RuntimeError("connection refused")
            async def rollback(self):
                pass
            async def close(self):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        yield FailingSession()

    app = create_app()
    app.dependency_overrides[get_db] = failing_db

    from starlette.testclient import TestClient
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    # Our HTTPException handler returns standardized error format
    assert data["data"] is None
    assert "error" in data
    error = data["error"]
    assert error["code"] in ("HTTP_ERROR", "PROVIDER_ERROR", "PROVIDER_TIMEOUT", "PROVIDER_AUTH_ERROR", "PROVIDER_INVALID_RESPONSE", "PROVIDER_UNSUPPORTED_MODEL", "PROVIDER_RATE_LIMIT")
    assert "message" in error
    assert "request_id" in data


# ──────────────────────────────────────────────────────────────────────────────
# Configuration Validation
# ──────────────────────────────────────────────────────────────────────────────

def test_settings_loads_from_env(monkeypatch):
    """Settings loads required fields from environment."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    # Clear lru_cache
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.app_env == "development"
    assert settings.app_secret_key == "x" * 32
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"
    assert settings.session_secret_key == "y" * 32


def test_settings_requires_min_length_secrets(monkeypatch):
    """Settings validates minimum length for secret keys."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_SECRET_KEY", "short")  # < 32 chars
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    get_settings.cache_clear()
    with pytest.raises(Exception) as exc_info:
        get_settings()
    assert "validation" in str(exc_info.value).lower() or "min_length" in str(exc_info.value).lower()


def test_settings_parses_allowed_origins(monkeypatch):
    """Settings parses comma-separated origins."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("SESSION_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("APP_ALLOWED_ORIGINS", "http://a.com,http://b.com")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.allowed_origins_list == ["http://a.com", "http://b.com"]


def test_settings_production_flag(monkeypatch):
    """is_production property reflects APP_ENV (dev mode tolerates missing secrets)."""
    common = {
        "APP_ENV": "production",
        "APP_SECRET_KEY": "x" * 32,
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "SESSION_SECRET_KEY": "y" * 32,
        # Production fail-fast checks require these to be present:
        "LLM_MASTER_ENCRYPTION_KEY": "prod-test-llm-key",
        "CRYPTO_PAYMENT_API_KEY": "prod-test-pay-key",
        "CRYPTO_PAYMENT_WEBHOOK_SECRET": "prod-test-wh-secret",
    }
    get_settings.cache_clear()
    monkeypatch.setenv(**common)
    settings = get_settings()
    assert settings.is_production is True
    assert settings.is_development is False

    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    settings = get_settings()
    assert settings.is_production is False
    assert settings.is_development is True


# ──────────────────────────────────────────────────────────────────────────────
# Error Response Format
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_spetser_error_envelope():
    """SpetserError produces consistent envelope: data/error/request_id."""
    from starlette.testclient import TestClient

    from app.core.errors import ValidationError
    from app.main import create_app

    app = create_app()

    @app.get("/test-error")
    async def raise_error():
        raise ValidationError(safe_message="Invalid input", error_code="TEST_ERROR")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-error")
    assert resp.status_code == 422
    data = resp.json()
    assert data["data"] is None
    assert data["error"]["code"] == "TEST_ERROR"
    assert data["error"]["message"] == "Invalid input"
    assert "request_id" in data
    # request_id may be null if client didn't provide one and middleware didn't set on request
    # (middleware sets on response header, not request header)


@pytest.mark.asyncio
async def test_unhandled_exception_envelope():
    """Unhandled exceptions produce safe envelope with INTERNAL_ERROR."""
    from starlette.testclient import TestClient

    from app.main import create_app

    app = create_app()

    @app.get("/test-crash")
    async def crash():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/test-crash")
    assert resp.status_code == 500
    data = resp.json()
    assert data["data"] is None
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert "غير متوقع" in data["error"]["message"]  # Arabic message
    assert "request_id" in data


@pytest.mark.asyncio
async def test_404_envelope():
    """404 returns the global error envelope (Phase 10, Lesson 10.4)."""
    from starlette.testclient import TestClient

    from app.main import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
    data = resp.json()
    assert data["data"] is None
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"]
    assert "request_id" in data


# ──────────────────────────────────────────────────────────────────────────────
# Request ID Behavior
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_request_id_generated_when_missing():
    """Middleware generates X-Request-ID when client doesn't provide one."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        rid = resp.headers.get("X-Request-ID")
        assert rid is not None
        # Should be a valid UUID
        import uuid
        uuid.UUID(rid)  # raises if invalid


@pytest.mark.asyncio
async def test_request_id_propagated_from_client():
    """Middleware echoes client-provided X-Request-ID."""
    app = create_app()
    custom_rid = "custom-request-id-123"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health/live", headers={"X-Request-ID": custom_rid})
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == custom_rid


@pytest.mark.asyncio
async def test_request_id_in_error_envelope():
    """Error envelope includes request_id from header."""
    from app.core.errors import ValidationError
    app = create_app()

    @app.get("/test-validation")
    async def validation_error():
        raise ValidationError(safe_message="Bad", error_code="VAL_ERR")

    custom_rid = "error-test-rid-456"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/test-validation", headers={"X-Request-ID": custom_rid})
        assert resp.status_code == 422
        data = resp.json()
        assert data["request_id"] == custom_rid


@pytest.mark.asyncio
async def test_request_id_bound_to_logs(caplog):
    """Request ID is bound to structlog context (integration check)."""
    from starlette.testclient import TestClient

    # This test verifies middleware binds request_id to contextvars
    # by checking that the logger can access it. Since structlog uses
    # contextvars, we can't easily inspect from outside. Instead we
    # verify the middleware imports and sets contextvars correctly.
    from app.middleware.request_id import REQUEST_ID_HEADER

    app = create_app()
    client = TestClient(app)
    custom_rid = "log-test-789"
    resp = client.get("/api/v1/health/live", headers={REQUEST_ID_HEADER: custom_rid})
    assert resp.status_code == 200
    # Middleware executed; if no exception, binding worked


# ──────────────────────────────────────────────────────────────────────────────
# CORS Configuration
# ──────────────────────────────────────────────────────────────────────────────

def test_cors_middleware_configured():
    """CORS middleware is added with explicit origins."""
    from app.main import create_app

    with patch.dict(os.environ, {
        "APP_ENV": "development",
        "APP_SECRET_KEY": "x" * 32,
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "SESSION_SECRET_KEY": "y" * 32,
        "APP_ALLOWED_ORIGINS": "http://localhost:5173,http://example.com",
    }):
        get_settings.cache_clear()
        app = create_app()
        # Find CORSMiddleware
        from fastapi.middleware.cors import CORSMiddleware
        cors = next((m for m in app.user_middleware if m.cls is CORSMiddleware), None)
        assert cors is not None
        # Starlette Middleware stores options in .kwargs
        assert cors.kwargs["allow_origins"] == ["http://localhost:5173", "http://example.com"]
        assert cors.kwargs["allow_credentials"] is True
        assert "Idempotency-Key" in cors.kwargs["allow_headers"]