"""
app/api/v1/routes/admin/users.py
─────────────────────────────────
Admin user management (Phase 8, Lesson 8.4).

Endpoints:
- GET    /api/v1/admin/users                 — list (search, filter, page)
- GET    /api/v1/admin/users/{id}            — detail
- POST   /api/v1/admin/users/{id}/adjust-credits — audited wallet adjust
- POST   /api/v1/admin/users/{id}/ban        — ban (blocks login/chat)
- POST   /api/v1/admin/users/{id}/unban      — restore to active
- GET    /api/v1/admin/users/{id}/transactions — credit ledger history
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin, get_developer
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models.credit_ledger import CreditLedger
from app.models.student import Student
from app.services.admin.audit_log_service import AuditLogService
from app.services.credit_service import CreditService

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


class CreditAdjustRequest(BaseModel):
    amount: Decimal = Field(description="Positive=credit, negative=debit")
    reason: str = Field(min_length=3, max_length=500)
    idempotency_key: str | None = Field(
        default=None, max_length=100,
        description="Optional replay guard; auto-generated when omitted.")


def _serialize(s: Student) -> dict:
    return {
        "id": str(s.id),
        "email": s.email,
        "display_name": s.display_name,
        "role": s.role,
        "status": s.status,
        "credit_balance": str(s.credit_balance),
        "is_premium": s.is_premium,
        "premium_expires_at": s.premium_expires_at.isoformat() if s.premium_expires_at else None,
        "failed_login_attempts": s.failed_login_attempts,
        "locked_until": s.locked_until.isoformat() if s.locked_until else None,
        "referral_code": s.referral_code,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


async def _get_user(db: AsyncSession, user_id: uuid.UUID) -> Student:
    user = (await db.execute(
        select(Student).where(Student.id == user_id)
    )).scalar_one_or_none()
    if user is None:
        raise NotFoundError("المستخدم غير موجود.")
    return user


# ── Reads (developer+) ──────────────────────────────────────────────────────

@router.get("")
async def list_users(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, max_length=200, description="Search email/name"),
    role: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Student)
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Student.email).like(pattern))
    if role:
        stmt = stmt.where(Student.role == role)
    if status:
        stmt = stmt.where(Student.status == status)
    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()
    users = (await db.execute(
        stmt.order_by(desc(Student.created_at)).limit(limit).offset(offset)
    )).scalars().all()
    return {"items": [_serialize(u) for u in users], "total": total,
            "limit": limit, "offset": offset}


@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    return _serialize(await _get_user(db, user_id))


@router.get("/{user_id}/transactions")
async def user_transactions(
    user_id: uuid.UUID,
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Credit ledger history for one user."""
    await _get_user(db, user_id)
    rows = (await db.execute(
        select(CreditLedger)
        .where(CreditLedger.student_id == user_id)
        .order_by(desc(CreditLedger.created_at))
        .limit(limit).offset(offset)
    )).scalars().all()
    return {
        "items": [{
            "id": str(r.id),
            "credits_charged": str(r.credits_charged),
            "balance_after": str(r.balance_after) if r.balance_after is not None else None,
            "entry_type": r.entry_type,
            "description": r.description,
            "reference_type": r.reference_type,
            "reference_id": str(r.reference_id) if r.reference_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows],
        "limit": limit, "offset": offset,
    }


# ── Mutations (admin+) ──────────────────────────────────────────────────────

@router.post("/{user_id}/adjust-credits")
async def adjust_credits(
    user_id: uuid.UUID,
    body: CreditAdjustRequest,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Adjust a user's credit balance. Every call is audited with a reason."""
    user = await _get_user(db, user_id)
    if body.amount == 0:
        raise ValidationError("المبلغ لا يمكن أن يكون صفرًا.")

    # CreditService.admin_adjust_credits writes its own audit row
    # (action="credit.admin_adjust") — no duplicate needed here.
    # Service semantics: positive delta = debit; API semantics: positive
    # amount = credit, so we negate. The service syncs `user.credit_balance`
    # in-session after the transaction (returns only the delta magnitude).
    service = CreditService(db, user)
    await service.admin_adjust_credits(
        -body.amount,
        admin=admin,
        reason=body.reason,
        idempotency_key=body.idempotency_key or f"admin-adj-{uuid.uuid4().hex}",
        correlation_id=getattr(request.state, "request_id", None),
    )
    return {"user_id": str(user_id), "credit_balance": str(user.credit_balance)}


@router.post("/{user_id}/ban")
async def ban_user(
    user_id: uuid.UUID,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ban a user: status → banned, session_version bumped (kills sessions)."""
    user = await _get_user(db, user_id)
    if user.id == admin.id:
        raise ConflictError("لا يمكنك حظر حسابك الخاص.")
    if user.role == "superadmin":
        raise ConflictError("لا يمكن حظر حساب superadmin.")
    user.status = "banned"
    user.session_version += 1
    await db.commit()
    await AuditLogService(db).log_action(
        actor_id=admin.id, action="user.banned",
        resource_type="student", resource_id=str(user_id),
        metadata={"email": user.email},
        correlation_id=getattr(request.state, "request_id", None),
    )
    return {"user_id": str(user_id), "status": user.status}


@router.post("/{user_id}/unban")
async def unban_user(
    user_id: uuid.UUID,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unban a user: status → active, failed_login_attempts reset."""
    user = await _get_user(db, user_id)
    user.status = "active"
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    await AuditLogService(db).log_action(
        actor_id=admin.id, action="user.unbanned",
        resource_type="student", resource_id=str(user_id),
        metadata={"email": user.email},
        correlation_id=getattr(request.state, "request_id", None),
    )
    return {"user_id": str(user_id), "status": user.status}
