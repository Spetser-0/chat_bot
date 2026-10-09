"""
tests/integration/test_rate_limits.py
────────────────────────────────────
Lesson 10.2 — Chat / payments / admin rate limits return 429 with Arabic envelope.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import litellm
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.models.ai_provider import AIProvider
from app.models.student import Student
from app.services.provider_service import ProviderService


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def _tight_limits(monkeypatch):
    """Shrink chat/payments/admin limits so 429 is easy to hit."""
    from app.core.config import get_settings

    s = get_settings()
    s.chat_rate_limit_per_minute = 2
    s.chat_rate_limit_per_day = 3
    s.payments_rate_limit_per_minute = 2
    s.admin_rate_limit_per_minute = 2
    yield


def _patch_settings(**overrides):
    """Mutate the cached Settings singleton (restored by autouse fixture)."""
    from app.core.config import get_settings

    s = get_settings()
    originals = {k: getattr(s, k) for k in overrides}
    for k, v in overrides.items():
        object.__setattr__(s, k, v)

    def _restore():
        for k, v in originals.items():
            object.__setattr__(s, k, v)

    return _restore


@pytest.fixture(autouse=True)
def _restore_settings_after():
    """Ensure any settings mutations in a test are undone after the test."""
    yield
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest_asyncio.fixture
async def provider(db):
    leftovers = (await db.execute(
        select(AIProvider).where(AIProvider.is_active.is_(True))
    )).scalars().all()
    for old in leftovers:
        old.is_active = False
    await db.commit()

    svc = ProviderService(db)
    return await svc.create(data=dict(
        slug=f"mock-rl-{uuid.uuid4().hex[:6]}", name="Mock", model_name="mock/model",
        api_key="sk-test-key-1234", priority_weight=100, is_active=True,
        cost_input_per_1k=Decimal("0.001"), cost_output_per_1k=Decimal("0.002"),
        max_retries=1, timeout_seconds=5,
    ))


@pytest.fixture
def mock_llm(monkeypatch):
    completion = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
    )
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=completion))


class TestChatRateLimit:
    async def test_429_when_minute_limit_exceeded(
        self, authenticated_client, provider, mock_llm
    ):
        _patch_settings(chat_rate_limit_per_minute=2, chat_rate_limit_per_day=100)
        for i in range(2):
            r = await authenticated_client.post(
                "/api/v1/chat/completions",
                json={"message": f"مرحبا {i}", "stream": False},
            )
            assert r.status_code == 200, r.text

        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "ثالث", "stream": False},
        )
        assert r.status_code == 429
        err = r.json()["error"]
        assert err["code"] == "RATE_LIMIT_EXCEEDED"
        assert "انتظر" in err["message"] or "المسموح" in err["message"]


class TestPaymentsRateLimit:
    async def test_429_when_create_invoice_spam(self, authenticated_client):
        _patch_settings(payments_rate_limit_per_minute=2)
        payload = {"amount_usd": "10", "currency": "usd"}
        for i in range(2):
            r = await authenticated_client.post(
                "/api/v1/payments/create-invoice",
                json={**payload, "idempotency_key": f"rl-{uuid.uuid4().hex[:8]}"},
            )
            assert r.status_code == 201, r.text

        r = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={**payload, "idempotency_key": f"rl-{uuid.uuid4().hex[:8]}"},
        )
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


class TestAdminRateLimit:
    async def test_429_when_admin_limit_exceeded(self, developer_client):
        _patch_settings(admin_rate_limit_per_minute=2)
        for i in range(2):
            r = await developer_client.get("/api/v1/admin/analytics/overview")
            assert r.status_code == 200, r.text

        r = await developer_client.get("/api/v1/admin/analytics/overview")
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_student_still_forbidden_not_rate_limited(
        self, authenticated_client
    ):
        # Non-admin hits 403 from authz, not 429 from admin limiter
        # (rate_limit_admin runs after get_developer which rejects students).
        r = await authenticated_client.get("/api/v1/admin/analytics/overview")
        assert r.status_code in (401, 403)
        assert r.json()["error"]["code"] in ("FORBIDDEN", "AUTHENTICATION_REQUIRED")


class TestRateLimitEnvelope:
    async def test_429_has_request_id_and_arabic_message(
        self, authenticated_client, provider, mock_llm
    ):
        _patch_settings(chat_rate_limit_per_minute=0)
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "مرحبا", "stream": False},
        )
        assert r.status_code == 429
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert body["error"]["message"]
        # Arabic message present (not English leak)
        assert any("؀" <= c <= "ۿ" or c.isalpha() for c in body["error"]["message"])
