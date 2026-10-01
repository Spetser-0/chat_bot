"""
app/services/admin/feature_routing_service.py
────────────────────────────────────────────────
Feature Routing management service for Developer Dashboard.
CRUD operations for feature routing rules with tier-based model selection.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.feature_configuration import FeatureConfiguration
from app.models.routing_rule import RoutingRule
from app.models.model_configuration import ModelConfiguration
from app.services.admin.model_config_service import ModelConfigService
from app.services.routing import resolve_routing

if TYPE_CHECKING:
    from app.services.providers.base import AIProvider


class FeatureRoutingService:
    """Service for managing feature routing rules."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._model_config_service = ModelConfigService(db)

    async def list_routing_rules(self) -> list[dict]:
        """List all routing rules with resolved model info."""
        result = await self._db.execute(
            select(RoutingRule).order_by(RoutingRule.feature_key, RoutingRule.tier)
        )
        rules = result.scalars().all()

        result_list = []
        for rule in rules:
            primary = await self._resolve_model_info(rule.primary_model_configuration_id)
            fallbacks = []
            for fb_id in rule.fallback_model_configuration_ids or []:
                fb_info = await self._get_model_info(fb_id)
                if fb_info:
                    fallbacks.append(fb_info)

            result_list.append({
                "id": str(rule.id),
                "feature_key": rule.feature_key,
                "tier": rule.tier,
                "max_retries": rule.max_retries,
                "timeout_seconds": rule.timeout_seconds,
                "temperature": rule.temperature,
                "enabled": rule.enabled,
                "primary": primary,
                "fallbacks": fallbacks,
            })
        return result_list

    async def get_routing_rule(self, feature_key: str, tier: str) -> dict | None:
        """Get routing rule for feature and tier."""
        result = await self._db.execute(
            select(RoutingRule).where(
                RoutingRule.feature_key == feature_key,
                RoutingRule.tier == tier,
            )
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            return None

        primary = await self._resolve_model_info(rule.primary_model_configuration_id)
        fallbacks = []
        for fb_id in rule.fallback_model_configuration_ids or []:
            fb_info = await self._get_model_info(fb_id)
            if fb_info:
                fallbacks.append(fb_info)

        return {
            "id": str(rule.id),
            "feature_key": rule.feature_key,
            "tier": rule.tier,
            "max_retries": rule.max_retries,
            "timeout_seconds": rule.timeout_seconds,
            "temperature": rule.temperature,
            "enabled": rule.enabled,
            "primary": primary,
            "fallbacks": fallbacks,
        }

    async def create_routing_rule(
        self,
        *,
        feature_key: str,
        tier: str,
        primary_model_configuration_id: uuid.UUID,
        fallback_model_configuration_ids: list[uuid.UUID] | None = None,
        max_retries: int = 1,
        timeout_seconds: int = 60,
        temperature: float | None = None,
        enabled: bool = True,
    ) -> dict:
        """Create a new routing rule."""
        # Verify feature exists
        feature_result = await self._db.execute(
            select(FeatureConfiguration).where(FeatureConfiguration.feature_key == feature_key)
        )
        if not feature_result.scalar_one_or_none():
            raise NotFoundError(f"Feature '{feature_key}' not found")

        # Verify primary model exists and is enabled
        primary = await self._model_config_service.get_config(primary_model_configuration_id)
        if not primary.enabled:
            raise ConflictError("Primary model configuration is disabled")

        # Verify fallbacks
        fallback_ids = fallback_model_configuration_ids or []
        for fb_id in fallback_ids:
            fb = await self._model_config_service.get_config(fb_id)
            if not fb.enabled:
                raise ConflictError(f"Fallback model {fb_id} is disabled")

        rule = RoutingRule(
            id=uuid.uuid4(),
            feature_key=feature_key,
            tier=tier,
            primary_model_configuration_id=primary_model_configuration_id,
            fallback_model_configuration_ids=fallback_ids or [],
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            enabled=enabled,
        )
        self._db.add(rule)
        await self._db.commit()
        await self._db.refresh(rule)

        return await self.get_routing_rule(feature_key, tier)

    async def update_routing_rule(
        self,
        rule_id: uuid.UUID,
        *,
        primary_model_configuration_id: uuid.UUID | None = None,
        fallback_model_configuration_ids: list[uuid.UUID] | None = None,
        max_retries: int | None = None,
        timeout_seconds: int | None = None,
        temperature: float | None = None,
        enabled: bool | None = None,
    ) -> dict:
        """Update a routing rule."""
        result = await self._db.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise NotFoundError("Routing rule not found")

        if primary_model_configuration_id is not None:
            primary = await self._model_config_service.get_config(primary_model_configuration_id)
            if not primary.enabled:
                raise ConflictError("Primary model configuration is disabled")
            rule.primary_model_configuration_id = primary_model_configuration_id

        if fallback_model_configuration_ids is not None:
            for fb_id in fallback_model_configuration_ids:
                fb = await self._model_config_service.get_config(fb_id)
                if not fb.enabled:
                    raise ConflictError(f"Fallback model {fb_id} is disabled")
            rule.fallback_model_configuration_ids = fallback_model_configuration_ids

        if max_retries is not None:
            rule.max_retries = max_retries
        if timeout_seconds is not None:
            rule.timeout_seconds = timeout_seconds
        if temperature is not None:
            rule.temperature = temperature
        if enabled is not None:
            rule.enabled = enabled

        await self._db.commit()
        await self._db.refresh(rule)

        return await self.get_routing_rule(rule.feature_key, rule.tier)

    async def delete_routing_rule(self, rule_id: uuid.UUID) -> None:
        """Delete a routing rule."""
        result = await self._db.execute(select(RoutingRule).where(RoutingRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            raise NotFoundError("Routing rule not found")

        await self._db.delete(rule)
        await self._db.commit()

    async def _resolve_model_info(self, model_config_id: uuid.UUID | None) -> dict | None:
        """Resolve model configuration to display info."""
        if model_config_id is None:
            return None
        return await self._get_model_info(model_config_id)

    async def _get_model_info(self, model_config_id: uuid.UUID) -> dict | None:
        """Get model info for display."""
        config = await self._model_config_service.get_config(model_config_id)
        if not config:
            return None
        return {
            "id": str(config.id),
            "model_name": config.model_name,
            "provider": config.provider.provider_key if config.provider else None,
            "tier": config.tier,
            "capabilities": config.capabilities_json,
            "max_tokens": config.max_tokens,
        }