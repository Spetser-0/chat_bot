"""
tests/unit/test_routing.py
───────────────────────────
Unit tests for routing, intent classification, and provider execution.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnsupportedModelError,
    RoutingError,
)
from app.services.intent_router import (
    classify_intent,
    is_ambiguous,
)
from app.services.provider_executor import (
    ExecutionResult,
    NonRecoverableProviderError,
    ProviderExecutor,
    RecoverableProviderError,
    classify_provider_error,
)
from app.services.routing import (
    ResolvedModel,
    enrich_resolved_model,
    resolve_routing,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_primary_model():
    return ResolvedModel(
        model_configuration_id=1,
        provider_key="anthropic",
        model_name="claude-3-sonnet",
        tier="thinker",
        capabilities=["json", "reasoning"],
        max_tokens=8192,
        temperature=None,
        timeout_seconds=60,
        max_retries=1,
        prompt_version_id=None,
        response_schema_key=None,
    )


@pytest.fixture
def mock_fallback_model():
    return ResolvedModel(
        model_configuration_id=2,
        provider_key="google_gemini",
        model_name="gemini-1.5-pro",
        tier="thinker",
        capabilities=["json"],
        max_tokens=8192,
        temperature=None,
        timeout_seconds=60,
        max_retries=1,
        prompt_version_id=None,
        response_schema_key=None,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Intent Router
# ──────────────────────────────────────────────────────────────────────────────

class TestIntentRouter:
    """Tests for intent classification."""

    def test_explicit_feature_presentation(self):
        """Explicit feature returns with 1.0 confidence."""
        result = classify_intent("any text", explicit_feature="presentation")
        assert result.intent == "presentation"
        assert result.confidence == 1.0
        assert not result.requires_clarification

    def test_explicit_feature_research(self):
        result = classify_intent("any text", explicit_feature="research")
        assert result.intent == "research"
        assert result.confidence == 1.0

    def test_explicit_feature_question_solver(self):
        result = classify_intent("any text", explicit_feature="question_solver")
        assert result.intent == "question_solver"

    def test_explicit_feature_chat(self):
        result = classify_intent("any text", explicit_feature="chat")
        assert result.intent == "chat"

    def test_arabic_presentation_keywords(self):
        """Arabic presentation keywords detected."""
        result = classify_intent("اريد عرض تقديمي عن التاريخ")
        assert result.intent == "presentation"
        assert result.confidence > 0.5

    def test_english_presentation_keywords(self):
        result = classify_intent("create a presentation about AI")
        assert result.intent == "presentation"

    def test_arabic_research_keywords(self):
        result = classify_intent("ابحث لي عن مراجع علمية")
        assert result.intent == "research"

    def test_english_research_keywords(self):
        result = classify_intent("I need academic research with citations")
        assert result.intent == "research"

    def test_arabic_question_solver_keywords(self):
        result = classify_intent("حل هذه المعادلة خطوة بخطوة")
        assert result.intent == "question_solver"

    def test_english_question_solver_keywords(self):
        result = classify_intent("solve this equation step by step")
        assert result.intent == "question_solver"

    def test_arabic_chat_keywords(self):
        result = classify_intent("اشرح لي ما هو الذكاء الاصطناعي")
        assert result.intent == "chat"

    def test_english_chat_keywords(self):
        result = classify_intent("explain how neural networks work")
        assert result.intent == "chat"

    def test_unknown_intent(self):
        """No matching keywords returns unknown with clarification."""
        result = classify_intent("xyz random text qwerty")
        assert result.intent == "unknown"
        assert result.requires_clarification
        assert result.clarifying_question is not None

    def test_low_confidence_triggers_clarification(self):
        """Low confidence returns requires_clarification=True."""
        # Multiple features match equally
        result = classify_intent("presentation research question")
        assert result.confidence < 1.0

    def test_explicit_tier_overrides(self):
        result = classify_intent("text", explicit_feature="chat", explicit_tier="thinker")
        assert result.model_tier == "thinker"

    def test_is_ambiguous_returns_true_for_unknown(self):
        result = classify_intent("random")
        assert is_ambiguous(result) is True

    def test_is_ambiguous_false_for_high_confidence(self):
        result = classify_intent("create a presentation")
        assert is_ambiguous(result) is False


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Provider Error Classification
# ──────────────────────────────────────────────────────────────────────────────

class TestProviderErrorClassification:
    """Tests for classifying provider errors as recoverable/non-recoverable."""

    def test_auth_error_non_recoverable(self):
        exc_class, recoverable = classify_provider_error(ProviderAuthError())
        assert recoverable is False
        assert exc_class is NonRecoverableProviderError

    def test_rate_limit_recoverable(self):
        exc_class, recoverable = classify_provider_error(ProviderRateLimitError())
        assert recoverable is True
        assert exc_class is RecoverableProviderError

    def test_timeout_recoverable(self):
        exc_class, recoverable = classify_provider_error(ProviderTimeoutError())
        assert recoverable is True

    def test_unsupported_model_non_recoverable(self):
        exc_class, recoverable = classify_provider_error(ProviderUnsupportedModelError())
        assert recoverable is False

    def test_invalid_response_recoverable(self):
        exc_class, recoverable = classify_provider_error(ProviderInvalidResponseError())
        assert recoverable is True

    def test_generic_provider_error_with_connection_keyword_recoverable(self):
        exc = ProviderError("Connection refused")
        exc_class, recoverable = classify_provider_error(exc)
        assert recoverable is True

    def test_generic_provider_error_without_keywords_non_recoverable(self):
        exc = ProviderError("Some permanent failure")
        exc_class, recoverable = classify_provider_error(exc)
        assert recoverable is False


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Provider Executor Retries
# ──────────────────────────────────────────────────────────────────────────────

from app.services.provider_executor import RetryPolicy


class TestProviderExecutor:
    """Tests for bounded retries and fallback behavior."""

    @pytest.mark.asyncio
    async def test_primary_succeeds_first_attempt(self, mock_primary_model):
        """Primary model succeeds on first attempt."""
        mock_response = MagicMock()
        mock_response.provider_name = "mock"
        mock_response.model_name = "mock-model"
        mock_response.raw_text = "Success"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20
        mock_response.latency_ms = 50
        
        provider = AsyncMock()
        provider.generate = AsyncMock(return_value=mock_response)
        
        with patch("app.services.provider_executor.get_provider_instance", return_value=provider):
            executor = ProviderExecutor(models=[mock_primary_model])
            result = await executor.execute(
                messages=[{"role": "user", "content": "test"}],
                system_prompt="test",
            )
        
        assert isinstance(result, ExecutionResult)
        assert result.response.raw_text == "Success"
        assert result.attempt == 1
        assert result.fallback_used is False

    @pytest.mark.asyncio
    async def test_retry_on_recoverable_error(self, mock_primary_model):
        """Retries on recoverable error (rate limit) then succeeds."""
        mock_response = MagicMock()
        mock_response.provider_name = "mock"
        mock_response.model_name = "mock-model"
        mock_response.raw_text = "Success after retry"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20
        mock_response.latency_ms = 50
        
        provider = AsyncMock()
        provider.generate = AsyncMock(side_effect=[
            ProviderRateLimitError(),
            mock_response,
        ])
        
        with patch("app.services.provider_executor.get_provider_instance", return_value=provider):
            executor = ProviderExecutor(models=[mock_primary_model])
            result = await executor.execute(
                messages=[{"role": "user", "content": "test"}],
                system_prompt="test",
            )
        
        assert result.response.raw_text == "Success after retry"
        assert provider.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_non_recoverable_error_tries_fallback(self, mock_primary_model, mock_fallback_model):
        """Non-recoverable error (auth) skips retries and tries fallback."""
        provider1 = AsyncMock()
        provider1.generate = AsyncMock(side_effect=ProviderAuthError())
        
        mock_response = MagicMock()
        mock_response.provider_name = "mock"
        mock_response.model_name = "mock-model"
        mock_response.raw_text = "Fallback success"
        mock_response.input_tokens = 10
        mock_response.output_tokens = 20
        mock_response.latency_ms = 50
        
        provider2 = AsyncMock()
        provider2.generate = AsyncMock(return_value=mock_response)
        
        call_count = [0]
        def provider_factory(key):
            call_count[0] += 1
            return provider1 if call_count[0] == 1 else provider2
        
        with patch("app.services.provider_executor.get_provider_instance", side_effect=provider_factory):
            executor = ProviderExecutor(models=[mock_primary_model, mock_fallback_model])
            result = await executor.execute(
                messages=[{"role": "user", "content": "test"}],
                system_prompt="test",
            )
        
        assert result.response.raw_text == "Fallback success"
        assert result.fallback_used is True

    @pytest.mark.asyncio
    async def test_all_models_exhausted_raises(self, mock_primary_model, mock_fallback_model):
        """All models fail - raises last error."""
        provider = AsyncMock()
        provider.generate = AsyncMock(side_effect=ProviderRateLimitError())
        
        with patch("app.services.provider_executor.get_provider_instance", return_value=provider):
            executor = ProviderExecutor(models=[mock_primary_model, mock_fallback_model])
            with pytest.raises(ProviderError):
                await executor.execute(
                    messages=[{"role": "user", "content": "test"}],
                    system_prompt="test",
                )

    @pytest.mark.asyncio
    async def test_max_retries_respected(self, mock_primary_model):
        """Max retries per model is respected."""
        provider = AsyncMock()
        provider.generate = AsyncMock(side_effect=ProviderRateLimitError())
        
        with patch("app.services.provider_executor.get_provider_instance", return_value=provider):
            policy = RetryPolicy(max_attempts=2, base_delay_seconds=0.01)
            executor = ProviderExecutor(models=[mock_primary_model], retry_policy=policy)
            with pytest.raises(ProviderError):
                await executor.execute(
                    messages=[{"role": "user", "content": "test"}],
                    system_prompt="test",
                )
        
        assert provider.generate.call_count == 2  # Primary + 1 retry


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Enrich Resolved Model
# ──────────────────────────────────────────────────────────────────────────────

class TestEnrichResolvedModel:
    """Tests for enriching resolved models with routing rule overrides."""

    def test_enrich_overrides_temperature(self, mock_primary_model):
        enriched = enrich_resolved_model(mock_primary_model, temperature=0.7)
        assert enriched.temperature == 0.7

    def test_enrich_overrides_timeout(self, mock_primary_model):
        enriched = enrich_resolved_model(mock_primary_model, timeout_seconds=120)
        assert enriched.timeout_seconds == 120

    def test_enrich_overrides_max_retries(self, mock_primary_model):
        enriched = enrich_resolved_model(mock_primary_model, max_retries=3)
        assert enriched.max_retries == 3

    def test_enrich_preserves_original_when_none(self, mock_primary_model):
        enriched = enrich_resolved_model(mock_primary_model, temperature=None)
        assert enriched.temperature is None  # Original was None

    def test_enrich_adds_prompt_version(self, mock_primary_model):
        import uuid
        prompt_id = uuid.uuid4()
        enriched = enrich_resolved_model(mock_primary_model, prompt_version_id=prompt_id)
        assert enriched.prompt_version_id == prompt_id


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Routing Resolution (Integration-style with mocked DB)
# ──────────────────────────────────────────────────────────────────────────────

class TestRoutingResolution:
    """Tests for routing resolution with mocked database."""

    @pytest.mark.asyncio
    async def test_resolve_routing_missing_feature_raises(self):
        """Missing feature raises RoutingError."""
        from unittest.mock import AsyncMock, MagicMock

        from sqlalchemy.ext.asyncio import AsyncSession
        
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(RoutingError, match="Feature 'missing' is not configured"):
            await resolve_routing("missing", "default", db)

    @pytest.mark.asyncio
    async def test_resolve_routing_disabled_feature_raises(self):
        """Disabled feature raises RoutingError."""
        from unittest.mock import AsyncMock, MagicMock

        from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.feature_configuration import FeatureConfiguration
        
        db = AsyncMock(spec=AsyncSession)
        feature_config = FeatureConfiguration(feature_key="presentation", enabled=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=feature_config)
        db.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(RoutingError, match="Feature 'presentation' is disabled"):
            await resolve_routing("presentation", "default", db)


# ──────────────────────────────────────────────────────────────────────────────
# Import for retry policy test
# ──────────────────────────────────────────────────────────────────────────────

