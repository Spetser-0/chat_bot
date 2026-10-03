"""
tests/unit/test_providers.py
──────────────────────────────
Unit tests for the provider abstraction layer.
"""
from __future__ import annotations

import pytest

from app.core.errors import ProviderError
from app.services.providers.base import ProviderResponse
from app.services.providers.mock_provider import MockProvider


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_returns_normalized_response(self):
        provider = MockProvider(fixed_text="Hello world", input_tokens=50, output_tokens=100)
        response = await provider.generate(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="You are helpful.",
            model="mock-model",
        )
        assert isinstance(response, ProviderResponse)
        assert response.provider_name == "mock"
        assert response.raw_text == "Hello world"
        assert response.input_tokens == 50
        assert response.output_tokens == 100
        assert response.total_tokens == 150

    @pytest.mark.asyncio
    async def test_structured_output_returned(self):
        structured = {"title": "Test", "slides": []}
        provider = MockProvider(fixed_structured=structured)
        response = await provider.generate(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="",
            model="mock-model",
        )
        assert response.structured_output == structured
        assert response.raw_text is None

    @pytest.mark.asyncio
    async def test_raises_configured_exception(self):
        error = ProviderError("Test error")
        provider = MockProvider(raise_on_generate=error)
        with pytest.raises(ProviderError):
            await provider.generate(
                messages=[{"role": "user", "content": "test"}],
                system_prompt="",
                model="mock-model",
            )

    @pytest.mark.asyncio
    async def test_call_count_increments(self):
        provider = MockProvider()
        assert provider.call_count == 0
        await provider.generate(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="",
            model="mock-model",
        )
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_last_call_kwargs_recorded(self):
        provider = MockProvider()
        await provider.generate(
            messages=[{"role": "user", "content": "hello"}],
            system_prompt="System",
            model="my-model",
            temperature=0.5,
        )
        assert provider.last_call_kwargs is not None
        assert provider.last_call_kwargs["model"] == "my-model"
        assert provider.last_call_kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_health_check_returns_true(self):
        provider = MockProvider(health=True)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false(self):
        provider = MockProvider(health=False)
        assert await provider.health_check() is False
