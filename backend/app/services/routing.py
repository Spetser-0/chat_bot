"""
app/services/routing.py
────────────────────────
Model routing service.

Resolves (feature, tier) → ordered list of ModelConfigurations.
Handles disabled providers, health checks, and fallback ordering.
Never returns hardcoded provider names — only validated DB records.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RoutingError
from app.models.feature_configuration import FeatureConfiguration
from app.models.model_configuration import ModelConfiguration
from app.models.prompt_version import PromptVersion
from app.models.provider import ModelProvider
from app.models.routing_rule import RoutingRule

if TYPE_CHECKING:
    from app.services.providers.base import AIProvider


@dataclass(frozen=True)
class ResolvedModel:
    """
    A single resolved model configuration with its provider.
    Ready to be passed to a provider adapter.
    """
    model_configuration_id: uuid.UUID
    provider_key: str        # e.g. "anthropic", "google_gemini"
    model_name: str          # e.g. "claude-3-sonnet-20240229"
    tier: str                # fast | default | thinker
    capabilities: list[str] | None
    max_tokens: int | None
    temperature: float | None
    timeout_seconds: int
    max_retries: int
    prompt_version_id: uuid.UUID | None
    response_schema_key: str | None


@dataclass(frozen=True)
class RoutingResolution:
    """
    Result of routing a (feature, tier) request.
    Contains the primary model and ordered fallbacks.
    """
    feature_key: str
    tier: str
    primary: ResolvedModel
    fallbacks: list[ResolvedModel]
    feature_enabled: bool
    feature_default_tier: str


async def resolve_routing(
    feature_key: str,
    tier: str,
    db: AsyncSession,
) -> RoutingResolution:
    """
    Resolve the routing rule for a feature and tier.
    
    Returns RoutingResolution with primary and fallback ResolvedModels.
    Raises RoutingError if no enabled routing rule exists.
    """
    # 1. Get feature configuration
    feature_result = await db.execute(
        select(FeatureConfiguration).where(
            FeatureConfiguration.feature_key == feature_key
        )
    )
    feature_config = feature_result.scalar_one_or_none()
    
    if feature_config is None:
        raise RoutingError(f"Feature '{feature_key}' is not configured.")
    
    if not feature_config.enabled:
        raise RoutingError(f"Feature '{feature_key}' is disabled.")
    
    # 2. Get routing rule for feature + tier
    rule_result = await db.execute(
        select(RoutingRule).where(
            RoutingRule.feature_key == feature_key,
            RoutingRule.tier == tier,
        )
    )
    routing_rule = rule_result.scalar_one_or_none()
    
    if routing_rule is None:
        # Try default tier if specific tier not found
        rule_result = await db.execute(
            select(RoutingRule).where(
                RoutingRule.feature_key == feature_key,
                RoutingRule.tier == feature_config.default_tier,
            )
        )
        routing_rule = rule_result.scalar_one_or_none()
        
        if routing_rule is None:
            raise RoutingError(
                f"No routing rule for feature '{feature_key}' tier '{tier}' "
                f"(default tier '{feature_config.default_tier}' also not found)."
            )
    
    if not routing_rule.enabled:
        raise RoutingError(f"Routing for '{feature_key}' + '{tier}' is disabled.")
    
    # 3. Resolve primary model
    primary_model = await _resolve_model_configuration(
        routing_rule.primary_model_configuration_id, db
    )
    
    # 4. Resolve fallback models
    fallback_models: list[ResolvedModel] = []
    fallback_ids = routing_rule.fallback_model_configuration_ids or []
    for fb_id in fallback_ids:
        try:
            fb_model = await _resolve_model_configuration(uuid.UUID(fb_id), db)
            fallback_models.append(fb_model)
        except Exception:
            # Skip invalid fallbacks silently (could log in production)
            pass
    
    return RoutingResolution(
        feature_key=feature_key,
        tier=tier,
        primary=primary_model,
        fallbacks=fallback_models,
        feature_enabled=feature_config.enabled,
        feature_default_tier=feature_config.default_tier,
    )


async def _resolve_model_configuration(
    model_config_id: uuid.UUID | None,
    db: AsyncSession,
) -> ResolvedModel:
    """Resolve a ModelConfiguration ID to a ResolvedModel with provider info."""
    if model_config_id is None:
        raise RoutingError("Model configuration ID is None.")
    
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ModelConfiguration)
        .options(selectinload(ModelConfiguration.provider))
        .join(ModelProvider)
        .where(
            ModelConfiguration.id == model_config_id,
            ModelConfiguration.enabled.is_(True),
            ModelProvider.enabled.is_(True),
        )
    )
    model_config = result.scalar_one_or_none()
    
    if model_config is None:
        raise RoutingError(
            f"Model configuration {model_config_id} not found, disabled, "
            f"or its provider is disabled."
        )
    
    return ResolvedModel(
        model_configuration_id=model_config.id,
        provider_key=model_config.provider.provider_key,
        model_name=model_config.model_name,
        tier=model_config.tier,
        capabilities=model_config.capabilities_json,
        max_tokens=model_config.max_tokens,
        temperature=None,  # Will be overridden by routing rule if set
        timeout_seconds=60,  # Default, overridden by routing rule
        max_retries=1,       # Default, overridden by routing rule
        prompt_version_id=None,  # Set by caller
        response_schema_key=None,  # Set by caller
    )


async def resolve_prompt_version(
    feature_key: str,
    db: AsyncSession,
) -> PromptVersion | None:
    """
    Resolve the active prompt version for a feature.
    Returns None if no active prompt exists (uses default).
    """
    feature_result = await db.execute(
        select(FeatureConfiguration).where(
            FeatureConfiguration.feature_key == feature_key
        )
    )
    feature_config = feature_result.scalar_one_or_none()
    
    if feature_config is None or feature_config.active_prompt_version_id is None:
        return None
    
    prompt_result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.id == feature_config.active_prompt_version_id,
            PromptVersion.status == "active",
        )
    )
    return prompt_result.scalar_one_or_none()


async def get_provider_instance(
    provider_key: str,
) -> AIProvider:
    """
    Get a provider adapter instance by provider key.
    Delegates to the registry.
    """
    from app.services.providers.registry import get_provider
    return get_provider(provider_key)


def enrich_resolved_model(
    model: ResolvedModel,
    *,
    prompt_version_id: uuid.UUID | None = None,
    response_schema_key: str | None = None,
    timeout_seconds: int | None = None,
    max_retries: int | None = None,
    temperature: float | None = None,
) -> ResolvedModel:
    """
    Enrich a ResolvedModel with routing-rule-level overrides.
    """
    return ResolvedModel(
        model_configuration_id=model.model_configuration_id,
        provider_key=model.provider_key,
        model_name=model.model_name,
        tier=model.tier,
        capabilities=model.capabilities,
        max_tokens=model.max_tokens,
        temperature=temperature if temperature is not None else model.temperature,
        timeout_seconds=timeout_seconds if timeout_seconds is not None else model.timeout_seconds,
        max_retries=max_retries if max_retries is not None else model.max_retries,
        prompt_version_id=prompt_version_id,
        response_schema_key=response_schema_key or model.response_schema_key,
    )