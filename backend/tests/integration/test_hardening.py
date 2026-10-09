"""
tests/integration/test_hardening.py
────────────────────────────────────
Lesson 10.6 — hardening acceptance suite.

Covers the Phase 10 checklist:
- 429 rate limiting (chat + payments)
- Long message rejected (API level)
- Invalid skill → safe 404
- No secret leak in chat responses or logs
- Auth required on chat
- Admin forbidden for students
- Error envelope on validation
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
from app.schemas.chat import MAX_MESSAGE_CHARS
from app.services.provider_service import ProviderService


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _restore_settings():
    yield
    from app.core.config import get_settings

    get_settings.cache_clear()


def _patch(**overrides):
    from app.core.config import get_settings

    s = get_settings()
    originals = {k: getattr(s, k) for k in overrides}
    for k, v in overrides.items():
        object.__setattr__(s, k, v)

    def _restore():
        for k, v in originals.items():
            object.__setattr__(s, k, v)

    return _restore


@pytest_asyncio.fixture
async def provider(db):
    leftovers = (await db.execute(
        select(AIProvider).where(AIProvider.is_active.is_(True))
    )).scalars().all()
    for old in leftovers:
        old.is_active = False
    await db.commit()
    return await ProviderService(db).create(data=dict(
        slug=f"mock-hard-{uuid.uuid4().hex[:6]}", name="Mock", model_name="mock/model",
        api_key="sk-LEAK-CANARY-KEY-12345", priority_weight=100, is_active=True,
        cost_input_per_1k=Decimal("0.001"), cost_output_per_1k=Decimal("0.002"),
        max_retries=1, timeout_seconds=5,
    ))


@pytest.fixture
def mock_llm(monkeypatch):
    completion = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        choices=[SimpleNamespace(message=SimpleNamespace(content="تمام"))],
    )
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=completion))


class TestHardeningAcceptance:
    async def test_unauthenticated_chat_rejected(self, client):
        r = await client.post(
            "/api/v1/chat/completions", json={"message": "hi", "stream": False}
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    async def test_long_message_rejected(
        self, authenticated_client, provider, mock_llm
    ):
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "x" * (MAX_MESSAGE_CHARS + 1), "stream": False},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_invalid_skill_safe_404(
        self, authenticated_client, provider, mock_llm
    ):
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "hi", "skill_slug": "no-such-skill", "stream": False},
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"

    async def test_api_key_never_in_response_or_logs(
        self, authenticated_client, provider, mock_llm, capsys
    ):
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "مرحبا", "stream": False},
        )
        assert r.status_code == 200
        body_text = r.text
        assert "sk-LEAK-CANARY-KEY-12345" not in body_text

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "sk-LEAK-CANARY-KEY-12345" not in combined

    async def test_chat_429_rate_limit(
        self, authenticated_client, provider, mock_llm
    ):
        _patch(chat_rate_limit_per_minute=1, chat_rate_limit_per_day=50)
        r1 = await authenticated_client.post(
            "/api/v1/chat/completions", json={"message": "أولاً", "stream": False}
        )
        assert r1.status_code == 200
        r2 = await authenticated_client.post(
            "/api/v1/chat/completions", json={"message": "ثانياً", "stream": False}
        )
        assert r2.status_code == 429
        assert r2.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_payments_429_rate_limit(self, authenticated_client):
        _patch(payments_rate_limit_per_minute=1)
        key1 = f"hard-{uuid.uuid4().hex[:8]}"
        key2 = f"hard-{uuid.uuid4().hex[:8]}"
        r1 = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "currency": "usd", "idempotency_key": key1},
        )
        assert r1.status_code == 201
        r2 = await authenticated_client.post(
            "/api/v1/payments/create-invoice",
            json={"amount_usd": "10", "currency": "usd", "idempotency_key": key2},
        )
        assert r2.status_code == 429
        assert r2.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_admin_forbidden_for_student(self, authenticated_client):
        r = await authenticated_client.get("/api/v1/admin/analytics/overview")
        assert r.status_code in (401, 403)
        assert r.json()["error"]["code"] in (
            "FORBIDDEN",
            "AUTHENTICATION_REQUIRED",
        )

    async def test_control_chars_stripped_from_message(
        self, authenticated_client, provider, mock_llm
    ):
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "مرح\x00با", "stream": False},
        )
        assert r.status_code == 200
        # The stored user message must not contain NUL
        from app.models.conversation import Conversation
        from app.models.message import Message, MessageRole

        conv_id = r.json()["conversation_id"]
        rows = (await authenticated_client.get(
            f"/api/v1/conversations/{conv_id}"
        )).json()
        contents = [m["content"] for m in rows.get("messages", [])]
        for c in contents:
            assert "\x00" not in c
