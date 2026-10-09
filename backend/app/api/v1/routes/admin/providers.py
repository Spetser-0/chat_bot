"""
app/api/v1/routes/admin/providers.py
─────────────────────────────────────
Admin management of AI providers (Phase 8, Lesson 8.2).

Security rules:
- API keys are NEVER returned in any response — only a masked preview.
- Reads: developer+ (dashboards need the list).
- Mutations: admin+ only, each writing an audit_logs row.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin, get_developer
from app.core.errors import ValidationError
from app.db.session import get_db
from app.models.ai_provider import AIProvider
from app.models.student import Student
from app.services.admin.audit_log_service import AuditLogService
from app.services.provider_service import ProviderService

router = APIRouter(prefix="/admin/providers", tags=["Admin - Providers"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    model_name: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    priority_weight: int = Field(default=100, ge=0, le=1000)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    cost_input_per_1k: Decimal = Field(default=Decimal("0.001"), ge=0)
    cost_output_per_1k: Decimal = Field(default=Decimal("0.002"), ge=0)
    is_active: bool = True
    is_primary: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    model_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_key: str | None = Field(default=None, min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)
    priority_weight: int | None = Field(default=None, ge=0, le=1000)
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    cost_input_per_1k: Decimal | None = Field(default=None, ge=0)
    cost_output_per_1k: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_primary: bool | None = None


def _serialize(provider: AIProvider, masked_key: str) -> dict[str, Any]:
    """Safe provider representation — masked key, never plaintext."""
    return {
        "id": str(provider.id),
        "name": provider.name,
        "slug": provider.slug,
        "model_name": provider.model_name,
        "base_url": provider.base_url,
        "api_key_masked": masked_key,
        "priority_weight": provider.priority_weight,
        "timeout_seconds": provider.timeout_seconds,
        "max_retries": provider.max_retries,
        "cost_input_per_1k": str(provider.cost_input_per_1k),
        "cost_output_per_1k": str(provider.cost_output_per_1k),
        "is_active": provider.is_active,
        "is_primary": provider.is_primary,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
    }


async def _audit(
    db: AsyncSession, actor: Student, action: str, provider: AIProvider,
    request: Request, metadata: dict | None = None,
) -> None:
    await AuditLogService(db).log_action(
        actor_id=actor.id,
        action=action,
        resource_type="ai_provider",
        resource_id=str(provider.id),
        metadata={"slug": provider.slug, **(metadata or {})},
        correlation_id=getattr(request.state, "request_id", None),
    )


# ── Reads (developer+) ──────────────────────────────────────────────────────

@router.get("")
async def list_providers(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """List all providers with masked API keys."""
    service = ProviderService(db)
    return [
        _serialize(p, service.masked_key_preview(p))
        for p in await service.list_all()
    ]


@router.get("/{slug}")
async def get_provider(
    slug: str,
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """Get one provider by slug (masked key)."""
    service = ProviderService(db)
    provider = await service.get_by_slug(slug)
    return _serialize(provider, service.masked_key_preview(provider))


# ── Mutations (admin+) ──────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_provider(
    body: ProviderCreate,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a provider. The API key is encrypted at rest."""
    service = ProviderService(db)
    data = body.model_dump()
    provider = await service.create(data=data)
    await _audit(db, admin, "provider.created", provider, request,
                 {"model_name": provider.model_name})
    return _serialize(provider, service.masked_key_preview(provider))


@router.patch("/{slug}")
async def update_provider(
    slug: str,
    body: ProviderUpdate,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a provider. Supplying api_key re-encrypts it."""
    service = ProviderService(db)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise ValidationError("لا توجد حقول للتحديث.")
    provider = await service.update(slug, data=data)
    await _audit(db, admin, "provider.updated", provider, request,
                 {"fields": sorted(data.keys())})
    return _serialize(provider, service.masked_key_preview(provider))


@router.delete("/{slug}", status_code=204)
async def delete_provider(
    slug: str,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a provider."""
    service = ProviderService(db)
    provider = await service.get_by_slug(slug)
    await service.delete(slug)
    await AuditLogService(db).log_action(
        actor_id=admin.id,
        action="provider.deleted",
        resource_type="ai_provider",
        resource_id=str(provider.id),
        metadata={"slug": slug},
        correlation_id=getattr(request.state, "request_id", None),
    )


@router.post("/{slug}/toggle-active")
async def toggle_provider(
    slug: str,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Flip is_active. Inactive providers are skipped by the router."""
    service = ProviderService(db)
    provider = await service.get_by_slug(slug)
    provider.is_active = not provider.is_active
    await db.commit()
    await db.refresh(provider)
    await _audit(db, admin, "provider.toggled", provider, request,
                 {"is_active": provider.is_active})
    return _serialize(provider, service.masked_key_preview(provider))


@router.post("/{slug}/test")
async def test_provider(
    slug: str,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Pre-flight check: provider active + API key decryptable.

    A real network ping is intentionally NOT performed here — this endpoint
    must never leak latency/cost side channels or hit paid APIs on demand.
    """
    service = ProviderService(db)
    provider = await service.get_by_slug(slug)
    try:
        await service.validate_for_call(provider)
        return {"healthy": True, "error": None}
    except ValidationError as exc:
        return {"healthy": False, "error": str(exc)}
    except Exception:
        return {"healthy": False, "error": "Provider configuration invalid."}
