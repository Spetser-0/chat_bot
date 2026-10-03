"""
app/services/admin/audit_log_service.py
────────────────────────────────────────
Audit Log service for Developer Dashboard.
Immutable audit trail for all developer actions.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogService:
    """Service for managing audit logs."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log_action(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Log an audit event."""
        log = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata,
            correlation_id=correlation_id,
        )
        self._db.add(log)
        await self._db.commit()

    async def get_audit_logs(
        self,
        *,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get audit logs with filters."""
        query = select(AuditLog).order_by(desc(AuditLog.created_at))

        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if from_date:
            query = query.where(AuditLog.created_at >= from_date)
        if to_date:
            query = query.where(AuditLog.created_at <= to_date)

        query = query.limit(limit).offset(offset)

        result = await self._db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "metadata": log.metadata_json,
                "correlation_id": log.correlation_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    async def get_audit_log(self, log_id: uuid.UUID) -> dict | None:
        """Get a specific audit log entry."""
        result = await self._db.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            return None

        return {
            "id": str(log.id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "metadata": log.metadata_json,
            "correlation_id": log.correlation_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }