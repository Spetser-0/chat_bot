"""
app/api/v1/routes/admin/settings.py
───────────────────────────────────
System settings management endpoints for admins.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.student import Student
from app.schemas.settings import SystemSettingsResponse, UpdateSettingsRequest
from app.services.settings_service import settings_service

router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])


@router.get("", response_model=SystemSettingsResponse)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """Retrieve global system settings."""
    return await settings_service.get_settings(db)


@router.patch("", response_model=SystemSettingsResponse)
async def update_system_settings(
    request: UpdateSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(require_admin),
):
    """Update global system settings (default credits, etc.)."""
    return await settings_service.update_settings(
        db,
        **request.model_dump(exclude_unset=True),
    )
