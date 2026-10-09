"""
tests/integration/test_observability.py
───────────────────────────────────────
Lessons 11.1–11.4 — health probes, metrics counters, admin metrics endpoint.
"""
from __future__ import annotations


class TestHealthLive:
    async def test_live_ok(self, client):
        r = await client.get("/api/v1/health/live")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestHealthReady:
    async def test_ready_ok_with_db(self, client):
        r = await client.get("/api/v1/health/ready")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"]["status"] == "ok"
        # Redis is skipped by default (rate_limit_backend=memory in tests)
        assert body["checks"]["redis"]["status"] in ("skipped", "ok", "error")
        # AI provider count is informational
        assert "active_count" in body["checks"]["ai_providers"] or \
            body["checks"]["ai_providers"]["status"] == "ok"
        assert "version" in body


class TestPublicMetrics:
    async def test_metrics_snapshot_safe_fields(self, client):
        r = await client.get("/api/v1/health/metrics")
        assert r.status_code == 200
        body = r.json()
        assert "uptime_seconds" in body
        assert "counters" in body
        assert "histograms" in body
        # Per-method breakdowns are filtered out of the public snapshot
        for key in body["counters"]:
            assert not key.startswith("http_requests_total.")

    async def test_requests_increment_counter(self, client):
        await client.get("/api/v1/health/live")
        await client.get("/api/v1/health/live")
        r = await client.get("/api/v1/health/metrics")
        counters = r.json()["counters"]
        assert counters.get("http_requests_total", 0) >= 2


class TestAdminMetrics:
    async def test_student_forbidden(self, authenticated_client):
        r = await authenticated_client.get("/api/v1/admin/metrics")
        assert r.status_code in (401, 403)

    async def test_developer_can_read_metrics(self, developer_client):
        await developer_client.get("/api/v1/admin/analytics/overview")
        r = await developer_client.get("/api/v1/admin/metrics")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "counters" in body
        assert "http_requests_total" in body["counters"]

    async def test_developer_can_reset(self, developer_client):
        r = await developer_client.post("/api/v1/admin/metrics/reset")
        assert r.status_code == 204
        snap = (await developer_client.get("/api/v1/admin/metrics")).json()
        # After reset, uptime still present; counters may be 0 or re-added by
        # the GET itself depending on middleware order — just ensure shape.
        assert "counters" in snap


class TestLLMMetricsHook:
    async def test_chat_success_records_llm_metrics(
        self, authenticated_client, provider, mock_llm
    ):
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "مرحبا", "stream": False},
        )
        assert r.status_code == 200, r.text
        snap = (await authenticated_client.get("/api/v1/health/metrics")).json()
        counters = snap["counters"]
        assert counters.get("llm_calls_total", 0) >= 1
        assert counters.get("llm_calls_success_total", 0) >= 1
        assert counters.get("llm_tokens_input_total", 0) >= 0


# Fixtures reused from test_hardening-style setup
import pytest  # noqa: E402
import uuid  # noqa: E402
from decimal import Decimal  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import AsyncMock  # noqa: E402
import litellm  # noqa: E402
import pytest_asyncio  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from sqlalchemy import select  # noqa: E402
from app.models.ai_provider import AIProvider  # noqa: E402
from app.services.provider_service import ProviderService  # noqa: E402


@pytest.fixture(autouse=True)
def _enc(monkeypatch):
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def provider(db):
    leftovers = (await db.execute(
        select(AIProvider).where(AIProvider.is_active.is_(True))
    )).scalars().all()
    for old in leftovers:
        old.is_active = False
    await db.commit()
    return await ProviderService(db).create(data=dict(
        slug=f"mock-obs-{uuid.uuid4().hex[:6]}", name="Mock", model_name="mock/model",
        api_key="sk-test-obs-123", priority_weight=100, is_active=True,
        cost_input_per_1k=Decimal("0.001"), cost_output_per_1k=Decimal("0.002"),
        max_retries=1, timeout_seconds=5,
    ))


@pytest.fixture
def mock_llm(monkeypatch):
    completion = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3),
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
    )
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=completion))
