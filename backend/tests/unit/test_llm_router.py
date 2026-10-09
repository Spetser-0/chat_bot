"""
tests/unit/test_llm_router.py
──────────────────────────────
Unit tests for LLMRouter (selection, failover, cost tracking).
litellm.acompletion is monkeypatched — no real network calls.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import litellm
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import ProviderError
from app.db.session import Base
from app.models.ai_provider import AIProvider  # noqa: F401
from app.services.llm.router import LLMRouter
from app.services.provider_service import ProviderService


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _provider(db, slug, *, weight=100, active=True, cost_in="0.001",
                    cost_out="0.002", retries=1):
    import uuid

    from app.core.security import encrypt_secret

    p = AIProvider(
        id=uuid.uuid4(),
        slug=slug, name=slug, model_name=f"{slug}-model",
        api_key_encrypted=encrypt_secret("sk-x-" + slug),
        priority_weight=weight, is_active=active, max_retries=retries,
        cost_input_per_1k=Decimal(cost_in),
        cost_output_per_1k=Decimal(cost_out),
    )
    db.add(p)
    await db.commit()
    return p


def _completion(in_tok=10, out_tok=5, text="hello"):
    return SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=in_tok, completion_tokens=out_tok),
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
    )


@pytest_asyncio.fixture
async def seeded(db):
    await _provider(db, "strong", weight=300)
    await _provider(db, "medium", weight=200)
    await _provider(db, "weak", weight=100)
    return db


class TestSelection:
    @pytest.mark.asyncio
    async def test_picks_highest_weight_first(self, seeded, monkeypatch):
        monkeypatch.setattr(litellm, "acompletion",
                            AsyncMock(return_value=_completion()))
        result = await LLMRouter(seeded).generate(
            messages=[{"role": "user", "content": "hi"}]
        )
        assert result.provider_slug == "strong"

    @pytest.mark.asyncio
    async def test_no_providers_raises(self, db):
        from app.core.errors import RoutingError

        with pytest.raises(RoutingError, match="No active"): 
            await LLMRouter(db).generate(messages=[])


class TestFailover:
    @pytest.mark.asyncio
    async def test_falls_over_on_rate_limit(self, seeded, monkeypatch):
        calls = []

        async def flaky(model, **kwargs):
            calls.append(model)
            if "strong" in model:
                raise litellm.RateLimitError(
                    "rl", model=model, llm_provider="x"
                )
            return _completion()

        monkeypatch.setattr(litellm, "acompletion", flaky)
        result = await LLMRouter(seeded).generate(
            messages=[{"role": "user", "content": "hi"}]
        )
        assert result.provider_slug == "medium"
        assert any("strong" in a for a in result.attempts)

    @pytest.mark.asyncio
    async def test_all_fail_raises_provider_error(self, seeded, monkeypatch):
        async def dead(model, **kwargs):
            raise litellm.Timeout("t", model=model, llm_provider="x")

        monkeypatch.setattr(litellm, "acompletion", dead)
        with pytest.raises(ProviderError, match="All providers failed"):
            await LLMRouter(seeded).generate(messages=[])


class TestCostTracking:
    @pytest.mark.asyncio
    async def test_cost_computed_from_tokens(self, db, monkeypatch):
        await _provider(db, "paid", cost_in="0.003", cost_out="0.015")
        monkeypatch.setattr(litellm, "acompletion",
                            AsyncMock(return_value=_completion(1000, 100)))
        result = await LLMRouter(db).generate(
            messages=[{"role": "user", "content": "hi"}]
        )
        # 1000 in * 0.003/1k + 100 out * 0.015/1k = 0.003 + 0.0015
        assert result.cost_usd == Decimal("0.004500")
        assert result.total_tokens == 1100


def _stream(parts):
    """Build an async iterable of streaming parts for litellm mock."""
    import litellm as _l
    from unittest.mock import AsyncMock as _AM

    async def _gen():
        for p in parts:
            yield p

    return _AM(side_effect=lambda **kw: _gen())


def _chunk(text=None, usage=None):
    delta = SimpleNamespace(content=text) if text is not None else None
    choice = SimpleNamespace(delta=delta) if delta is not None else None
    return SimpleNamespace(
        choices=[choice] if choice else [],
        usage=usage,
    )


class TestStreaming:
    @pytest.mark.asyncio
    async def test_emits_chunks_then_done(self, seeded, monkeypatch):
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=100)
        parts = [_chunk("أهلا"), _chunk(" وسهلا"), _chunk(None, usage)]
        monkeypatch.setattr(litellm, "acompletion", _stream(parts))

        events = [e async for e in LLMRouter(seeded).stream_complete(
            messages=[{"role": "user", "content": "hi"}]
        )]
        types = [e.type for e in events]
        assert types == ["start", "chunk", "chunk", "done"]
        assert events[1].data["text"] == "أهلا"
        done = events[-1].data
        assert done["input_tokens"] == 1000
        assert Decimal(done["cost_usd"]) > 0

    @pytest.mark.asyncio
    async def test_failover_before_first_token(self, seeded, monkeypatch):
        async def flaky(model, **kwargs):
            if "strong" in model:
                raise litellm.RateLimitError("rl", model=model, llm_provider="x")

            async def gen():
                yield _chunk("ok", SimpleNamespace(
                    prompt_tokens=1, completion_tokens=1))
            return gen()

        monkeypatch.setattr(litellm, "acompletion", flaky)
        events = [e async for e in LLMRouter(seeded).stream_complete(
            messages=[{"role": "user", "content": "hi"}]
        )]
        assert events[0].data["provider_slug"] == "medium"
        assert events[-1].type == "done"

    @pytest.mark.asyncio
    async def test_mid_stream_error_is_terminal_event(self, seeded, monkeypatch):
        async def boom():
            yield _chunk("partial")
            raise ConnectionError("drop")

        monkeypatch.setattr(litellm, "acompletion",
                            AsyncMock(side_effect=lambda **kw: boom()))
        events = [e async for e in LLMRouter(seeded).stream_complete(
            messages=[{"role": "user", "content": "hi"}]
        )]
        assert [e.type for e in events] == ["start", "chunk", "error"]
        assert events[-1].data["code"] == "provider_unavailable"

    @pytest.mark.asyncio
    async def test_no_providers_yields_error_event(self, db):
        events = [e async for e in LLMRouter(db).stream_complete(messages=[])]
        assert events[0].type == "error"
        assert events[0].data["code"] == "provider_unavailable"

    @pytest.mark.asyncio
    async def test_sse_frame_format(self, seeded, monkeypatch):
        parts = [_chunk("x", SimpleNamespace(prompt_tokens=1,
                                             completion_tokens=1))]
        monkeypatch.setattr(litellm, "acompletion", _stream(parts))
        frames = [e.to_sse() async for e in LLMRouter(seeded).stream_complete(
            messages=[{"role": "user", "content": "hi"}]
        )]
        for f in frames:
            assert f.startswith("event: ") and "\ndata: " in f and f.endswith("\n\n")
        assert '"text": "x"' in frames[1]

