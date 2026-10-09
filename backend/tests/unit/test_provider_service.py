"""
tests/unit/test_provider_service.py
────────────────────────────────────
Unit tests for the NEW provider service (app/services/provider_service.py)
covering the AIProvider model with Fernet-encrypted keys.

Uses in-memory SQLite async session. Depends on Phase 2 encryption
(LLM_MASTER_ENCRYPTION_KEY) being available via test fixtures/settings.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import decrypt_secret
from app.db.session import Base
from app.models.ai_provider import AIProvider  # noqa: F401 – registers model
from app.services.provider_service import ProviderService

TEST_KEY = "sk-test-abcdefghijklmnop"


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch):
    """Provide a deterministic Fernet key so encryption works in tests."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", key)
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        yield session
    await engine.dispose()


def _payload(**overrides) -> dict:
    base = dict(
        slug="anthropic-main",
        name="Anthropic Claude",
        model_name="claude-sonnet-4-5",
        priority_weight=100,
        timeout_seconds=30,
        max_retries=3,
        cost_input_per_1k=Decimal("0.003"),
        cost_output_per_1k=Decimal("0.015"),
        is_active=True,
        api_key=TEST_KEY,
    )
    base.update(overrides)
    return base


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_and_encrypts_key(self, db):
        svc = ProviderService(db)
        p = await svc.create(data=_payload())
        assert p.slug == "anthropic-main"
        assert p.api_key_encrypted != TEST_KEY
        assert decrypt_secret(p.api_key_encrypted) == TEST_KEY

    @pytest.mark.asyncio
    async def test_duplicate_slug_conflicts(self, db):
        svc = ProviderService(db)
        await svc.create(data=_payload())
        with pytest.raises(ConflictError):
            await svc.create(data=_payload())

    @pytest.mark.asyncio
    async def test_missing_key_rejected(self, db):
        svc = ProviderService(db)
        payload = _payload()
        payload.pop("api_key")
        with pytest.raises(ValidationError):
            await svc.create(data=payload)

    @pytest.mark.asyncio
    async def test_missing_slug_rejected(self, db):
        svc = ProviderService(db)
        with pytest.raises(ValidationError):
            await svc.create(data=_payload(slug=None))


class TestReads:
    @pytest.mark.asyncio
    async def test_list_active_orders_by_weight(self, db):
        svc = ProviderService(db)
        await svc.create(data=_payload(slug="low", priority_weight=10))
        await svc.create(data=_payload(slug="high", priority_weight=200))
        await svc.create(data=_payload(slug="off", is_active=False))
        slugs = [p.slug for p in await svc.list_active()]
        assert slugs == ["high", "low"]

    @pytest.mark.asyncio
    async def test_get_by_slug_missing_raises(self, db):
        with pytest.raises(NotFoundError):
            await ProviderService(db).get_by_slug("nope")


class TestUpdateDelete:
    @pytest.mark.asyncio
    async def test_update_rotates_key(self, db):
        svc = ProviderService(db)
        await svc.create(data=_payload())
        updated = await svc.update("anthropic-main", data={"api_key": "sk-new-9999"})
        assert decrypt_secret(updated.api_key_encrypted) == "sk-new-9999"

    @pytest.mark.asyncio
    async def test_delete_removes_row(self, db):
        svc = ProviderService(db)
        await svc.create(data=_payload())
        await svc.delete("anthropic-main")
        with pytest.raises(NotFoundError):
            await svc.get_by_slug("anthropic-main")


class TestValidation:
    @pytest.mark.asyncio
    async def test_inactive_provider_rejected(self, db):
        svc = ProviderService(db)
        p = await svc.create(data=_payload(is_active=False))
        with pytest.raises(ConflictError):
            await svc.validate_for_call(p)

    @pytest.mark.asyncio
    async def test_unknown_capability_rejected(self, db):
        svc = ProviderService(db)
        p = await svc.create(data=_payload())
        with pytest.raises(ValidationError):
            await svc.validate_for_call(p, capability="robtargett")

    @pytest.mark.asyncio
    async def test_masked_preview(self, db):
        svc = ProviderService(db)
        p = await svc.create(data=_payload())
        preview = svc.masked_key_preview(p)
        assert TEST_KEY not in preview
        assert preview.endswith(TEST_KEY[-4:])
