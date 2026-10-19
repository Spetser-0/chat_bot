"""
app/api/v1/routes/developer/api_keys.py
───────────────────────────────────────
Developer panel endpoints for API key lifecycle and customization.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.student import Student
from app.schemas.api_key import (
    APIKeyCreateResponse,
    APIKeyResponse,
    CreateAPIKeyRequest,
    UpdateAPIKeyRequest,
)
from app.services.api_key_service import api_key_service

router = APIRouter(prefix="/developer", tags=["Developer"])


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """List all API keys (admin/developer only)."""
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    return result.scalars().all()


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """
    Create a new API key with optional system prompt & daily credit limit.
    The plain API key is returned ONLY ONCE in the response.
    """
    api_key, plain_key = await api_key_service.create_key(
        db=db,
        name=request.name,
        created_by=str(current_user.id),
        system_prompt=request.system_prompt,
        max_credits_per_day=request.max_credits_per_day,
        allowed_skills=request.allowed_skills,
        expires_at=request.expires_at,
    )

    data = APIKeyResponse.model_validate(api_key).model_dump(mode="json")
    data["plain_key"] = plain_key
    return data


@router.patch("/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """Update API key settings and prompts."""
    updated = await api_key_service.update_key(
        db,
        key_id,
        **request.model_dump(exclude_unset=True),
    )
    return updated


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """Delete an API key."""
    await api_key_service.delete_key(db, key_id)
    return {"message": "API key deleted successfully."}


@router.post("/api-keys/{key_id}/regenerate", response_model=APIKeyCreateResponse)
async def regenerate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """Regenerate API key token value (previous token becomes immediately invalid)."""
    api_key, plain_key = await api_key_service.regenerate_key(db, key_id)
    data = APIKeyResponse.model_validate(api_key).model_dump(mode="json")
    data["plain_key"] = plain_key
    return data
