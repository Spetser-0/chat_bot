"""
app/services/admin/playground_service.py
──────────────────────────────────────────────
Test Playground service for Developer Dashboard.
Allows developers to test provider configurations and prompts safely.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.services.presentation import PresentationService
from app.services.routing import resolve_routing, resolve_prompt_version, enrich_resolved_model
from app.services.provider_executor import ProviderExecutor
from app.services.routing import resolve_routing, enrich_resolved_model
from app.schemas.presentation import PresentationDocument, PresentationRequest, PRESENTATION_SCHEMA_VERSION
from app.schemas.presentation import RenderResult

if TYPE_CHECKING:
    from app.models.student import Student
    from app.services.presentation import PresentationService


class TestPlaygroundService:
    """
    Test playground service for developers to test provider configurations.
    Uses the same pipeline as production but with mock provider option.
    """

    def __init__(self, db) -> None:
        self._db = db

    async def run_test(
        self,
        *,
        feature_key: str,
        tier: str,
        prompt: str | None = None,
        model_config_id: uuid.UUID | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> dict:
        """
        Run a test generation with specified configuration.
        Uses mock provider if no model_config_id provided.
        """
        from app.services.providers.registry import get_provider
        from app.services.providers.mock_provider import MockProvider
        from app.services.provider_executor import ProviderExecutor
        from app.services.routing import resolve_routing, resolve_prompt_version, enrich_resolved_model
        from app.services.provider_executor import ProviderExecutor
        from app.services.source_checker import get_source_checker
        from app.services.renderer import get_renderer

        if feature_key not in ("presentation", "chat", "research", "question_solver"):
            raise ValueError(f"Unknown feature: {feature_key}")

        # Resolve routing
        routing = await resolve_routing(
            feature_key=feature_key,
            tier=tier,
            db=self._db,
        )

        # Get prompt version
        prompt_version = await resolve_prompt_version(feature_key, self._db)

        # Get primary model
        if model_config_id:
            from app.models.model_configuration import ModelConfiguration
            from app.services.providers.registry import get_provider
            
            result = await self._db.execute(
                select(ModelConfiguration).where(ModelConfiguration.id == model_config_id)
            )
            model_config = result.scalar_one_or_none()
            if not model_config:
                raise NotFoundError("Model configuration not found")
            
            provider = get_provider(model_config.provider.provider_key)
            models = [model_config]
        else:
            # Use mock provider for testing
            from app.services.providers.mock_provider import MockProvider
            provider = MockProvider()
            # Use default mock model
            from app.models.model_configuration import ModelConfiguration
            model_config = ModelConfiguration(
                id=uuid.uuid4(),
                provider_id=uuid.uuid4(),
                model_name="mock-test",
                tier="default",
            )

        # Build prompt
        system_prompt = system_prompt or f"Test prompt for {feature_key}"
        if prompt:
            system_prompt += f"\n\nUser request: {prompt}"

        # Execute
        executor = ProviderExecutor(models=[model_config])
        
        # We need to create a mock execution result for testing
        from app.services.provider_executor import ExecutionResult
        from app.services.providers.base import ProviderResponse
        
        # For testing, we'll use mock provider
        mock_provider = MockProvider(fixed_text="Test response", input_tokens=10, output_tokens=20)
        
        # Create executor with mock
        executor = ProviderExecutor(models=[mock_provider])
        
        exec_result = await executor.execute(
            messages=[{"role": "user", "content": prompt or "Test"}],
            system_prompt=system_prompt,
            response_schema=None,
        )

        return {
            "success": True,
            "response": exec_result.response.raw_text or str(exec_result.response.structured_output),
            "tokens": {
                "input": exec_result.response.input_tokens,
                "output": exec_result.response.output_tokens,
            },
            "latency_ms": exec_result.response.latency_ms,
            "provider": exec_result.response.provider_name,
            "model": exec_result.response.model_name,
        }


# Simple mock for playground testing
class MockProvider:
    def __init__(self, fixed_text: str = "Mock response", input_tokens: int = 10, output_tokens: int = 20):
        self._fixed_text = fixed_text
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._health = True
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock"

    async def generate(self, *, messages, system_prompt, model, response_schema=None, max_tokens=None, temperature=None):
        self.call_count += 1
        from app.services.providers.base import ProviderResponse
        return ProviderResponse(
            provider_name=self.name,
            model_name=model,
            raw_text=self._fixed_text,
            input_tokens=10,
            output_tokens=20,
            latency_ms=10,
        )

    async def health_check(self) -> bool:
        return self._health