"""
app/api/v1/routes/admin/analytics.py
─────────────────────────────────────
Admin analytics endpoints (Phase 8, Lesson 8.6).

All endpoints are read-only (developer+). They aggregate directly from
the operational tables — no separate analytics store yet. If volume ever
demands it, these queries move behind a materialized view without
changing the API shape.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_developer
from app.db.session import get_db
from app.models.message import Message
from app.models.payment_invoice import PaymentInvoice, PaymentStatus
from app.models.referral import Referral, ReferralStatus
from app.models.reward_transaction import RewardStatus, RewardTransaction
from app.models.student import Student

router = APIRouter(prefix="/admin/analytics", tags=["Admin - Analytics"])


def _days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


# ── GET /admin/analytics/overview ───────────────────────────────────────────

@router.get("/overview")
async def analytics_overview(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """High-level platform health: users, messages, revenue, referrals."""
    total_users = (await db.execute(
        select(func.count(Student.id))
    )).scalar_one()
    new_users_7d = (await db.execute(
        select(func.count(Student.id)).where(
            Student.created_at >= _days_ago(7))
    )).scalar_one()

    total_messages = (await db.execute(
        select(func.count(Message.id))
    )).scalar_one()
    assistant_msgs_7d = (await db.execute(
        select(func.count(Message.id)).where(
            Message.role == "assistant",
            Message.created_at >= _days_ago(7))
    )).scalar_one()

    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(PaymentInvoice.amount_usd), 0)).where(
            PaymentInvoice.status == PaymentStatus.PAID)
    )).scalar_one()
    revenue_7d = (await db.execute(
        select(func.coalesce(func.sum(PaymentInvoice.amount_usd), 0)).where(
            PaymentInvoice.status == PaymentStatus.PAID,
            PaymentInvoice.paid_at >= _days_ago(7))
    )).scalar_one()

    total_referrals = (await db.execute(
        select(func.count(Referral.id))
    )).scalar_one()
    qualified_referrals = (await db.execute(
        select(func.count(Referral.id)).where(
            Referral.status.in_([ReferralStatus.QUALIFIED,
                                 ReferralStatus.REWARDED]))
    )).scalar_one()

    return {
        "users": {"total": total_users, "new_last_7d": new_users_7d},
        "messages": {"total": total_messages,
                     "assistant_last_7d": assistant_msgs_7d},
        "revenue": {"total_usd": str(total_revenue),
                    "usd_last_7d": str(revenue_7d)},
        "referrals": {"total": total_referrals,
                      "qualified": qualified_referrals,
                      "conversion_rate": (
                          round(qualified_referrals / total_referrals, 4)
                          if total_referrals else 0.0)},
    }


# ── GET /admin/analytics/llm-usage ──────────────────────────────────────────

@router.get("/llm-usage")
async def analytics_llm_usage(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Token usage and latency grouped by provider, model, and skill."""
    since = _days_ago(days)

    by_provider = (await db.execute(
        select(
            Message.provider_name,
            func.count(Message.id).label("messages"),
            func.coalesce(func.sum(Message.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(Message.output_tokens), 0).label("output_tokens"),
            func.avg(Message.latency_ms).label("avg_latency_ms"),
        )
        .where(Message.role == "assistant", Message.created_at >= since,
               Message.provider_name.is_not(None))
        .group_by(Message.provider_name)
    )).all()

    by_skill = (await db.execute(
        select(
            Message.skill_slug,
            func.count(Message.id).label("messages"),
            func.coalesce(func.sum(Message.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(Message.output_tokens), 0).label("output_tokens"),
        )
        .where(Message.role == "assistant", Message.created_at >= since,
               Message.skill_slug.is_not(None))
        .group_by(Message.skill_slug)
    )).all()

    return {
        "window_days": days,
        "by_provider": [{
            "provider_name": r[0],
            "messages": r[1],
            "input_tokens": int(r[2]),
            "output_tokens": int(r[3]),
            "avg_latency_ms": round(float(r[4]), 1) if r[4] is not None else None,
        } for r in by_provider],
        "by_skill": [{
            "skill_slug": r[0],
            "messages": r[1],
            "input_tokens": int(r[2]),
            "output_tokens": int(r[3]),
        } for r in by_skill],
    }


# ── GET /admin/analytics/revenue ────────────────────────────────────────────

@router.get("/revenue")
async def analytics_revenue(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """Revenue breakdown by status, plus paid-invoice count and average."""
    by_status = (await db.execute(
        select(
            PaymentInvoice.status,
            func.count(PaymentInvoice.id),
            func.coalesce(func.sum(PaymentInvoice.amount_usd), 0),
        ).group_by(PaymentInvoice.status)
    )).all()

    paid_stats = (await db.execute(
        select(
            func.count(PaymentInvoice.id),
            func.coalesce(func.sum(PaymentInvoice.amount_usd), 0),
            func.avg(PaymentInvoice.amount_usd),
        ).where(PaymentInvoice.status == PaymentStatus.PAID)
    )).one()

    paid_count, paid_total, paid_avg = paid_stats
    return {
        "by_status": [{
            "status": r[0], "count": r[1], "total_usd": str(r[2]),
        } for r in by_status],
        "paid": {
            "count": paid_count,
            "total_usd": str(paid_total),
            "average_usd": str(round(paid_avg, 2)) if paid_avg is not None else "0",
        },
    }


# ── GET /admin/analytics/referrals ──────────────────────────────────────────

@router.get("/referrals")
async def analytics_referrals(
    _: Student = Depends(get_developer),
    db: AsyncSession = Depends(get_db),
):
    """Referral funnel + reward liability."""
    by_status = (await db.execute(
        select(Referral.status, func.count(Referral.id))
        .group_by(Referral.status)
    )).all()

    pending_rewards = (await db.execute(
        select(
            func.count(RewardTransaction.id),
            func.coalesce(func.sum(RewardTransaction.amount), 0),
        ).where(RewardTransaction.status == RewardStatus.PENDING)
    )).one()

    paid_rewards = (await db.execute(
        select(
            func.count(RewardTransaction.id),
            func.coalesce(func.sum(RewardTransaction.amount), 0),
        ).where(RewardTransaction.status == RewardStatus.PAID)
    )).one()

    total_referrals = sum(r[1] for r in by_status)
    qualified = sum(r[1] for r in by_status
                    if r[0] in (ReferralStatus.QUALIFIED, ReferralStatus.REWARDED))

    return {
        "by_status": [{"status": r[0], "count": r[1]} for r in by_status],
        "total": total_referrals,
        "qualified": qualified,
        "conversion_rate": (round(qualified / total_referrals, 4)
                            if total_referrals else 0.0),
        "rewards": {
            "pending_count": pending_rewards[0],
            "pending_amount_usd": str(pending_rewards[1]),
            "paid_count": paid_rewards[0],
            "paid_amount_usd": str(paid_rewards[1]),
        },
    }
