"""
app/api/v1/routes/credits.py
─────────────────────────────
Credit wallet endpoints (Lesson 5.5).

GET  /api/v1/credits/balance          → own balance
GET  /api/v1/credits/history          → own ledger (paged)
POST /api/v1/credits/admin/adjust     → admin-only manual adjustment,
                                        audited in audit_logs
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_student, get_admin
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.student import Student
from app.schemas.credit import (
    AdminAdjustRequest,
    AdminAdjustResponse,
    BalanceResponse,
    HistoryResponse,
    LedgerEntryResponse,
)
from app.services.credit_service import CREDITS_PER_USD, CreditService
from sqlalchemy import select

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
):
    credits = CreditService(db, student)
    return BalanceResponse(
        balance=await credits.get_balance(), credits_per_usd=CREDITS_PER_USD,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    student: Student = Depends(get_active_student),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    credits = CreditService(db, student)
    rows = await credits.get_history(limit=limit, offset=offset)
    # Fast total for pagination UI
    from sqlalchemy import func
    from app.models.credit_ledger import CreditLedger

    total = (await db.execute(
        select(func.count())
        .select_from(CreditLedger)
        .where(CreditLedger.student_id == student.id)
    )).scalar_one()

    return HistoryResponse(
        entries=[LedgerEntryResponse(
            id=r.id, entry_type=r.entry_type,
            credits_charged=r.credits_charged, balance_after=r.balance_after,
            description=r.description, reference_type=r.reference_type,
            reference_id=r.reference_id,
            created_at=r.created_at.isoformat(),
        ) for r in rows],
        total=total,
    )


@router.post("/admin/adjust", response_model=AdminAdjustResponse)
async def admin_adjust(
    body: AdminAdjustRequest,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manual credit adjustment. Every call lands in `audit_logs`."""
    result = await db.execute(
        select(Student).where(Student.id == body.student_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFoundError("الطالب غير موجود.")
    if target.id == admin.id:
        # Prevent self-awarding: adjust your own wallet through payments.
        from app.core.errors import AuthorizationError
        raise AuthorizationError("لا يمكنك تعديل رصيدك بنفسك.")

    before = target.credit_balance
    credits = CreditService(db, target)
    changed = await credits.admin_adjust_credits(
        body.delta, admin=admin, reason=body.reason,
        idempotency_key=body.idempotency_key,
    )
    return AdminAdjustResponse(
        student_id=target.id, new_balance=before + body.delta,
        credits_changed=changed,
    )
