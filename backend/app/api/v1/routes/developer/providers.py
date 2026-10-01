"""
app/api/v1/routes/developer/providers.py
──────────────────────────────────────────
Developer Dashboard: Provider Management API.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_db
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.student import Student
from app.services.admin.provider_service import ProviderService

router = APIRouter(prefix="/providers", tags=["Developer - Providers"])


# ── Schemas ────────────────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    provider_key: str
    display_name: str
    api_key: str | None = None
    enabled: bool = True


class ProviderUpdate(BaseModel):
    display_name: str | None = None
    api_key: str | None = None
    enabled: bool | None = None


class ProviderResponse(BaseModel):
    id: uuid.UUID
    provider_key: str
    display_name: str
    enabled: bool
    health_status: str
    last_health_check_at: str | None
    last_error_message: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProviderTestResponse(BaseModel):
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """List all providers (developer only)."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    service = ProviderService(db)
    providers = await service.list_providers()
    return [
        ProviderResponse(
            id=p.id,
            provider_key=p.provider_key,
            display_name=p.display_name,
            enabled=p.enabled,
            health_status=p.health_status,
            last_health_check_at=p.last_health_check_at.isoformat() if p.last_health_check_at else None,
            last_error_message=p.last_error_message,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in providers
    ]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: uuid.UUID,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Get a provider by ID."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    service = ProviderService(db)
    provider = await service.get_provider(provider_id)
    return ProviderResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        display_name=provider.display_name,
        enabled=provider.enabled,
        health_status=provider.health_status,
        last_health_check_at=provider.last_health_check_at.isoformat() if provider.last_health_check_at else None,
        last_error_message=provider.last_error_message,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
    )


@router.post("", status_code=201, response_model=ProviderResponse)
async def create_provider(
    body: ProviderCreate,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Create a new provider."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    service = ProviderService(db)
    try:
        provider = await service.create_provider(
            provider_key=body.provider_key,
            display_name=body.display_name,
            api_key=body.api_key,
            enabled=body.enabled,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return ProviderResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        display_name=provider.display_name,
        enabled=provider.enabled,
        health_status=provider.health_status,
        last_health_check_at=provider.last_health_check_at.isoformat() if provider.last_health_check_at else None,
        last_error_message=provider.last_error_message,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
    )


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderUpdate,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Update a provider."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    service = ProviderService(db)
    try:
        provider = await service.update_provider(
            provider_id=provider_id,
            display_name=body.display_name,
            api_key=body.api_key,
            enabled=body.enabled,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Provider not found")

    return ProviderResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        display_name=provider.display_name,
        enabled=provider.enabled,
        health_status=provider.health_status,
        last_health_check_at=provider.last_health_check_at.isoformat() if provider.last_health_check_at else None,
        last_error_message=provider.last_error_message,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
    )


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: uuid.UUID,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Delete a provider."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    service = ProviderService(db)
    try:
        await service.delete_provider(provider_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider(
    provider_id: uuid.UUID,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Test provider connectivity."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    service = ProviderService(db)
    try:
        import time
        start = time.time()
        healthy = await service.test_provider(provider_id)
        latency = (time.time() - start) * 1000
        return ProviderTestResponse(healthy=healthy, latency_ms=latency)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/{provider_id}/rotate-key", response_model=ProviderResponse)
async def rotate_provider_key(
    provider_id: uuid.UUID,
    body: dict,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Rotate provider API key."""
    if current_student.role not in ("developer", "admin"):
        raise HTTPException(status_code=403, detail="Developer access required")

    new_key = body.get("api_key")
    if not new_key:
        raise HTTPException(status_code=400, detail="New API key required")

    service = ProviderService(db)
    try:
        provider = await service.rotate_key(provider_id, body["api_key"])
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Provider not found")

    return ProviderResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        display_name=provider.display_name,
        enabled=provider.enabled,
        health_status=provider.health_status,
        last_health_check_at=provider.last_health_check_at.isoformat() if provider.last_health_check_at else None,
        last_error_message=provider.last_error_message,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
    )