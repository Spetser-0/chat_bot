"""
tests/integration/test_chat_endpoint.py
────────────────────────────────────────
Integration tests for POST /api/v1/chat/completions (Lesson 3.9 / 3.10).

litellm.acompletion is monkeypatched — no real network. Providers are
seeded into the in-memory DB via ProviderService so encryption + the
router's selection path are exercised end to end.
"""
from __future__ import annotations

import json
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
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.skill import Skill
from app.models.student import Student
from app.services.provider_service import ProviderService


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def provider(db):
    # Shared session DB: deactivate leftovers from previous tests so the
    # router can only pick this test's provider.
    leftovers = (await db.execute(
        select(AIProvider).where(AIProvider.is_active.is_(True))
    )).scalars().all()
    for old in leftovers:
        old.is_active = False
    await db.commit()

    svc = ProviderService(db)
    slug = f"mock-primary-{uuid.uuid4().hex[:6]}"
    p = await svc.create(data=dict(
        slug=slug, name="Mock", model_name="mock/model",
        api_key="sk-test-key-1234", priority_weight=100, is_active=True,
        cost_input_per_1k=Decimal("0.001"), cost_output_per_1k=Decimal("0.002"),
        max_retries=1, timeout_seconds=5,
    ))
    return p


def _completion(text="أهلاً بك!", in_tok=10, out_tok=5):
    return SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=in_tok, completion_tokens=out_tok),
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
    )


@pytest_asyncio.fixture
async def mock_llm(monkeypatch):
    monkeypatch.setattr(litellm, "acompletion",
                        AsyncMock(return_value=_completion()))


class TestNonStreaming:
    @pytest.mark.asyncio
    async def test_json_response_and_persistence(
        self, authenticated_client, db, provider, mock_llm
    ):
        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "اشرح لي الجمع", "stream": False},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["text"] == "أهلاً بك!"
        assert body["provider_slug"] == provider.slug
        assert body["usage"]["input_tokens"] == 10

        msgs = (await db.execute(
            select(Message).where(Message.conversation_id == uuid.UUID(body["conversation_id"]))
            .order_by(Message.created_at)
        )).scalars().all()
        assert [m.role for m in msgs] == [MessageRole.USER, MessageRole.ASSISTANT]
        # cost column is Numeric(18,4) → micro-USD rounds to 0.0000; exact
        # value is exposed in usage.cost_usd. Widening scale: Phase 5 debt.
        assert msgs[1].cost_credits == Decimal("0.0000")
        assert msgs[1].input_tokens == 10

    @pytest.mark.asyncio
    async def test_reuses_existing_conversation(
        self, authenticated_client, db, provider, mock_llm, student
    ):
        conv = Conversation(id=uuid.uuid4(), user_id=student.id, title="t")
        db.add(conv)
        await db.commit()

        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "hi", "conversation_id": str(conv.id), "stream": False},
        )
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] == str(conv.id)

    @pytest.mark.asyncio
    async def test_invalid_skill_returns_404(
        self, authenticated_client, db, provider, mock_llm
    ):
        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "hi", "skill_slug": "no-such-skill", "stream": False},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_skill_system_prompt_used(
        self, authenticated_client, db, provider, mock_llm
    ):
        db.add(Skill(id=uuid.uuid4(), name="Math", slug="math-tutor",
                     system_prompt="You are a math teacher.",
                     temperature=0.3, max_tokens=256, is_public=True))
        await db.commit()

        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "2+2?", "skill_slug": "math-tutor", "stream": False},
        )
        assert resp.status_code == 200
        call = litellm.acompletion.call_args
        assert call.kwargs["messages"][0] == {
            "role": "system", "content": "You are a math teacher."
        }
        assert call.kwargs["max_tokens"] == 256

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client, db, provider):
        resp = await client.post(
            "/api/v1/chat/completions", json={"message": "hi", "stream": False}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_other_users_conversation_forbidden(
        self, authenticated_client, db, provider, mock_llm, developer
    ):
        conv = Conversation(id=uuid.uuid4(), user_id=developer.id, title="x")
        db.add(conv)
        await db.commit()
        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "hi", "conversation_id": str(conv.id), "stream": False},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_auto_skill_slug_classifies_and_chat_succeeds(
        self, authenticated_client, db, provider, mock_llm
    ):
        """skill_slug='auto' → classifier runs; junk answer → default (None)."""
        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "اشرح لي الجمع", "skill_slug": "auto",
                  "stream": False},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["skill_slug"] is None or isinstance(
            resp.json()["skill_slug"], str)

    @pytest.mark.asyncio
    async def test_empty_message_rejected(self, authenticated_client, db, provider):
        resp = await authenticated_client.post(
            "/api/v1/chat/completions", json={"message": "   ", "stream": False}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_provider_failure_gives_safe_error(
        self, authenticated_client, db, provider, monkeypatch
    ):
        async def dead(model, **kw):
            raise litellm.Timeout("t", model=model, llm_provider="x")

        monkeypatch.setattr(litellm, "acompletion", dead)
        resp = await authenticated_client.post(
            "/api/v1/chat/completions", json={"message": "hi", "stream": False}
        )
        assert resp.status_code == 502  # ProviderError → safe envelope
        assert "sk-test-key-1234" not in resp.text

    @pytest.mark.asyncio
    async def test_api_key_never_appears_in_logs(
        self, authenticated_client, db, provider, monkeypatch, caplog
    ):
        """Regression for Phase 3 acceptance: failover/errors must not log keys."""
        import logging

        secret = "sk-test-key-1234"

        async def dead(model, **kw):
            raise litellm.Timeout("t", model=model, llm_provider="x")

        monkeypatch.setattr(litellm, "acompletion", dead)
        with caplog.at_level(logging.DEBUG):
            await authenticated_client.post(
                "/api/v1/chat/completions", json={"message": "hi", "stream": False}
            )
            # streaming error path too
            await authenticated_client.post(
                "/api/v1/chat/completions", json={"message": "hi", "stream": True}
            )
        assert secret not in caplog.text


class TestCreditCharging:
    @pytest.mark.asyncio
    async def test_successful_chat_spends_credits(
        self, authenticated_client, db, provider, mock_llm, student
    ):
        from decimal import Decimal

        from sqlalchemy import select

        before = student.credit_balance
        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "اختبار الرصيد", "stream": False},
        )
        assert resp.status_code == 200
        after = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        # 10 in × 0.001/1k + 5 out × 0.002/1k = 0.00002 USD → 0.002 credits
        expected = Decimal("0.0020")
        assert before - after == expected, f"{before} - {after} != {expected}"

    @pytest.mark.asyncio
    async def test_failed_call_does_not_charge(
        self, authenticated_client, db, provider, monkeypatch, student
    ):
        from sqlalchemy import select

        async def dead(**kw):
            raise litellm.Timeout("t", model="m", llm_provider="x")

        monkeypatch.setattr(litellm, "acompletion", dead)
        resp = await authenticated_client.post(
            "/api/v1/chat/completions", json={"message": "hi", "stream": False}
        )
        assert resp.status_code == 502
        after = (await db.execute(
            select(Student.credit_balance).where(Student.id == student.id)
        )).scalar_one()
        assert after == student.credit_balance

    @pytest.mark.asyncio
    async def test_retry_never_double_charges(
        self, authenticated_client, db, provider, mock_llm, student
    ):
        from sqlalchemy import func, select

        resp1 = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "أول", "stream": False},
        )
        assert resp1.status_code == 200
        conv_id = resp1.json()["conversation_id"]

        resp2 = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "ثاني", "conversation_id": conv_id, "stream": False},
        )
        assert resp2.status_code == 200

        from app.models.credit_ledger import CreditLedger
        keys = (await db.execute(
            select(CreditLedger.idempotency_key)
            .where(CreditLedger.student_id == student.id)
        )).scalars().all()
        assert len(keys) == 2
        assert len(set(keys)) == 2  # distinct messages → distinct charges


class TestStreaming:
    @pytest.mark.asyncio
    async def test_sse_stream_with_done_event(
        self, authenticated_client, db, provider, monkeypatch
    ):
        def _chunk(text=None, usage=None):
            delta = SimpleNamespace(content=text) if text else None
            return SimpleNamespace(
                choices=[SimpleNamespace(delta=delta)] if delta else [],
                usage=usage,
            )

        async def fake_stream(**kw):
            async def gen():
                yield _chunk("مر")
                yield _chunk("حبا")
                yield _chunk(None, SimpleNamespace(prompt_tokens=3,
                                                   completion_tokens=2))
            return gen()

        monkeypatch.setattr(litellm, "acompletion", fake_stream)

        resp = await authenticated_client.post(
            "/api/v1/chat/completions", json={"message": "hi", "stream": True}
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = [line[6:] for line in resp.text.splitlines()
                  if line.startswith("data: ")]
        types = [json.loads(e) for e in events]
        texts = [e.get("text") for e in types if "text" in e]
        assert texts == ["مر", "حبا"]
        done = types[-1]
        assert done["input_tokens"] == 3
        conv_id = uuid.UUID(types[0]["conversation_id"])

        msgs = (await db.execute(select(Message)
                                 .where(Message.role == MessageRole.ASSISTANT,
                                        Message.conversation_id == conv_id))
                ).scalars().all()
        assert len(msgs) == 1 and msgs[0].content == "مرحبا"


class TestRegenerate:
    """Lesson 9.10: regenerate must not duplicate the user turn."""

    @pytest.mark.asyncio
    async def test_regenerate_requires_conversation_id(self, authenticated_client, provider, mock_llm):
        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "hi", "regenerate": True, "stream": False},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_regenerate_reuses_last_user_row(
        self, authenticated_client, db, provider, mock_llm, student
    ):
        # First turn creates user + assistant.
        first = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "اشرح المثلث", "stream": False},
        )
        assert first.status_code == 200
        conv_id = first.json()["conversation_id"]

        before = (await db.execute(
            select(Message).where(
                Message.conversation_id == uuid.UUID(conv_id),
                Message.role == MessageRole.USER,
            )
        )).scalars().all()
        assert len(before) == 1

        # Regenerate: no new user row; one more assistant row.
        second = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={
                "message": "اشرح المثلث",
                "conversation_id": conv_id,
                "regenerate": True,
                "stream": False,
            },
        )
        assert second.status_code == 200, second.text

        after_users = (await db.execute(
            select(Message).where(
                Message.conversation_id == uuid.UUID(conv_id),
                Message.role == MessageRole.USER,
            )
        )).scalars().all()
        after_assistants = (await db.execute(
            select(Message).where(
                Message.conversation_id == uuid.UUID(conv_id),
                Message.role == MessageRole.ASSISTANT,
            )
        )).scalars().all()
        assert len(after_users) == 1, "regenerate must not insert a duplicate user row"
        assert len(after_assistants) == 2

    @pytest.mark.asyncio
    async def test_regenerate_without_history_errors(
        self, authenticated_client, db, provider, mock_llm, student
    ):
        conv = Conversation(id=uuid.uuid4(), user_id=student.id, title="empty")
        db.add(conv)
        await db.commit()

        resp = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={
                "message": "hi",
                "conversation_id": str(conv.id),
                "regenerate": True,
                "stream": False,
            },
        )
        assert resp.status_code in (400, 422)
