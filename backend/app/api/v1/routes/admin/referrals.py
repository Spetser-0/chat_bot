"""
app/api/v1/routes/admin/referrals.py
────────────────────────────────────
Admin management of referrals (Phase 7, Lesson 7.6).

- GET  /api/v1/admin/referrals        — list (developer+, filters, paging)
- POST /api/v1/admin/referrals/{id}/revoke   — revoke referral + unpaid reward
- POST /api/v1/admin/referrals/{id}/release  — force-release held reward now
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin, get_developer
from app.db.session import get_db
from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardStatus, RewardTransaction
from app.models.student import Student
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/admin/referrals", tags=["Admin - Referrals"])


@router.get("", response_model=dict)
async def list_referrals(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter by referral status"),
    referrer_user_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Paginated referral listing with referrer/referred emails and reward info."""
    stmt = select(Referral)
    if status:
        stmt = stmt.where(Referral.status == status)
    if referrer_user_id:
        stmt = stmt.where(Referral.referrer_user_id == referrer_user_id)
    stmt = stmt.order_by(Referral.created_at.desc()).limit(limit).offset(offset)
    referrals = list((await db.execute(stmt)).scalars().all())

    user_ids = {r.referrer_user_id for r in referrals} | {r.referred_user_id for r in referrals}
    emails: dict[uuid.UUID, str] = {}
    if user_ids:
        for row in (await db.execute(
            select(Student.id, Student.email).where(Student.id.in_(user_ids))
        )).all():
            emails[row[0]] = row[1]

    reward_by_referral: dict[uuid.UUID, RewardTransaction] = {}
    if referrals:
        ref_ids = [r.id for r in referrals]
        for rw in (await db.execute(
            select(RewardTransaction).where(RewardTransaction.referral_id.in_(ref_ids))
        )).scalars().all():
            reward_by_referral[rw.referral_id] = rw

    items = []
    for r in referrals:
        reward = reward_by_referral.get(r.id)
        items.append({
            "id": str(r.id),
            "referrer_user_id": str(r.referrer_user_id),
            "referrer_email": emails.get(r.referrer_user_id),
            "referred_user_id": str(r.referred_user_id),
            "referred_email": emails.get(r.referred_user_id),
            "referral_code": r.referral_code,
            "status": r.status,
            "ip_address": r.ip_address,
            "device_fingerprint": r.device_fingerprint,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "qualified_at": r.qualified_at.isoformat() if r.qualified_at else None,
            "rewarded_at": r.rewarded_at.isoformat() if r.rewarded_at else None,
            "reward_amount": str(reward.amount) if reward else None,
            "reward_status": reward.status if reward else None,
        })
    return {"items": items, "count": len(items), "limit": limit, "offset": offset}


@router.post("/{referral_id}/revoke", response_model=dict)
async def revoke_referral(
    referral_id: uuid.UUID,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a referral; any unpaid reward is voided (Lesson 7.6)."""
    referral = await ReferralService(db).revoke_referral(referral_id)
    from app.services.admin.audit_log_service import AuditLogService
    await AuditLogService(db).log_action(
        actor_id=admin.id, action="referral.revoked",
        resource_type="referral", resource_id=str(referral.id),
        metadata={"status": referral.status},
        correlation_id=getattr(request.state, "request_id", None),
    )
    return {"id": str(referral.id), "status": referral.status}


@router.post("/{referral_id}/release", response_model=dict)
async def release_referral(
    referral_id: uuid.UUID,
    request: Request,
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Force-release a held reward immediately, skipping the holding period."""
    reward = await ReferralService(db).force_release_referral(referral_id)
    from app.services.admin.audit_log_service import AuditLogService
    await AuditLogService(db).log_action(
        actor_id=admin.id, action="referral.reward_released",
        resource_type="referral", resource_id=str(referral_id),
        metadata={"reward_id": str(reward.id), "amount": str(reward.amount)},
        correlation_id=getattr(request.state, "request_id", None),
    )
    return {
        "reward_id": str(reward.id),
        "amount": str(reward.amount),
        "status": reward.status,
    }


@router.post("/release-due", response_model=dict)
async def release_due_rewards(
    admin: Student = Depends(get_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Release every reward whose holding period has elapsed.

    Idempotent — safe to call repeatedly. A cron/worker will call this
    in Phase 12; exposed now for ops and tests.
    """
    released = await ReferralService(db).release_due_rewards()
    total = sum((r.amount for r in released), Decimal("0"))
    return {"released_count": len(released), "total_amount": str(total)}
