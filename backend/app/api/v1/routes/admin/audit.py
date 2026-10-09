"""
app/api/v1/routes/admin/audit.py
─────────────────────────────────
Audit log read endpoints (Phase 8, Lesson 8.7).

The audit trail is written by every admin mutation (skills, providers,
users, payments, referrals) via AuditLogService. This module exposes it
read-only to admins/developers for the dashboard.

Endpoints:
- GET /api/v1/admin/audit-logs          — list with filters (developer+)
- GET /api/v1/admin/audit-logs/{id}     — single entry (developer+)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_developer
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.student import Student
from app.services.admin.audit_log_service import AuditLogService

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin - Audit Logs"])


@router.get("")
async def list_audit_logs(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    actor_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None, max_length=100),
    resource_type: str | None = Query(None, max_length=100),
    resource_id: str | None = Query(None, max_length=255),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Filtered audit trail, newest first. Total count included for paging."""
    count_stmt = select(func.count(AuditLog.id))
    if actor_id:
        count_stmt = count_stmt.where(AuditLog.actor_id == actor_id)
    if action:
        count_stmt = count_stmt.where(AuditLog.action == action)
    if resource_type:
        count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        count_stmt = count_stmt.where(AuditLog.resource_id == resource_id)
    if from_date:
        count_stmt = count_stmt.where(AuditLog.created_at >= from_date)
    if to_date:
        count_stmt = count_stmt.where(AuditLog.created_at <= to_date)
    total = (await db.execute(count_stmt)).scalar_one()

    items = await AuditLogService(db).get_audit_logs(
        actor_id=actor_id, action=action, resource_type=resource_type,
        resource_id=resource_id, from_date=from_date, to_date=to_date,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{log_id}")
async def get_audit_log(
    log_id: uuid.UUID,
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    log = await AuditLogService(db).get_audit_log(log_id)
    if log is None:
        raise NotFoundError("سجل التدقيق غير موجود.")
    return log
