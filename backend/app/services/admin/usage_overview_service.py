"""
app/services/admin/usage_overview_service.py
──────────────────────────────────────────────
Usage Overview service for Developer Dashboard.
Aggregated usage statistics and cost analytics.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import desc, func, select

from app.models.credit_ledger import CreditLedger
from app.models.request import Request


class UsageOverviewService:
    """Service for aggregated usage statistics and cost analytics."""

    def __init__(self, db) -> None:
        self._db = db

    async def get_overview(self, *, days: int = 30) -> dict:
        """Get overall usage overview for the last N days."""
        since = datetime.now() - timedelta(days=days)

        # Total requests
        total_requests_result = await self._db.execute(
            select(func.count(Request.id)).where(Request.created_at >= since)
        )
        total_requests = total_requests_result.scalar() or 0

        # Successful requests
        successful_result = await self._db.execute(
            select(func.count(Request.id)).where(
                Request.created_at >= since,
                Request.status == "ready",
            )
        )
        successful_requests = successful_result.scalar() or 0

        # Failed requests
        failed_result = await self._db.execute(
            select(func.count(Request.id)).where(
                Request.created_at >= since,
                Request.status == "failed",
            )
        )
        failed_requests = failed_result.scalar() or 0

        # Total credits consumed
        credits_result = await self._db.execute(
            select(func.sum(CreditLedger.credits_charged)).where(
                CreditLedger.created_at >= since,
                CreditLedger.entry_type == "charge",
            )
        )
        total_credits = credits_result.scalar() or Decimal(0)

        # Total USD cost
        cost_result = await self._db.execute(
            select(func.sum(CreditLedger.computed_usd_cost)).where(
                CreditLedger.created_at >= since,
                CreditLedger.entry_type == "charge",
            )
        )
        total_usd = cost_result.scalar() or Decimal(0)

        # Active students
        active_students_result = await self._db.execute(
            select(func.count(func.distinct(Request.student_id))).where(
                Request.created_at >= since,
            )
        )
        active_students = active_students_result.scalar() or 0

        # Requests by feature
        feature_stats = await self._db.execute(
            select(Request.feature, func.count(Request.id))
            .where(Request.created_at >= since)
            .group_by(Request.feature)
        )
        feature_breakdown = {row[0]: row[1] for row in feature_stats}

        # Requests by tier
        tier_stats = await self._db.execute(
            select(Request.model_tier, func.count(Request.id))
            .where(Request.created_at >= since)
            .group_by(Request.model_tier)
        )
        tier_breakdown = {row[0]: row[1] for row in tier_stats}

        # Daily requests for chart
        daily_stats = await self._db.execute(
            select(
                func.date(Request.created_at).label("date"),
                func.count(Request.id).label("count"),
            )
            .where(Request.created_at >= since)
            .group_by(func.date(Request.created_at))
            .order_by(func.date(Request.created_at))
        )
        daily_chart = [
            {"date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]), "count": row[1]}
            for row in daily_stats
        ]

        return {
            "period_days": days,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round(successful_requests / total_requests * 100, 1) if total_requests > 0 else 0,
            "total_credits_consumed": float(total_credits),
            "total_usd_cost": float(total_usd),
            "active_students": active_students,
            "feature_breakdown": feature_breakdown,
            "tier_breakdown": tier_breakdown,
            "daily_chart": daily_chart,
        }

    async def get_student_usage(self, student_id: uuid.UUID, days: int = 30) -> dict:
        """Get usage statistics for a specific student."""
        since = datetime.now() - timedelta(days=days)

        # Requests
        req_result = await self._db.execute(
            select(func.count(Request.id)).where(
                Request.student_id == student_id,
                Request.created_at >= since,
            )
        )
        total_requests = req_result.scalar() or 0

        # Credits
        credits_result = await self._db.execute(
            select(func.sum(CreditLedger.credits_charged)).where(
                CreditLedger.student_id == student_id,
                CreditLedger.created_at >= since,
                CreditLedger.entry_type == "charge",
            )
        )
        credits = credits_result.scalar() or Decimal(0)

        # USD cost
        cost_result = await self._db.execute(
            select(func.sum(CreditLedger.computed_usd_cost)).where(
                CreditLedger.student_id == student_id,
                CreditLedger.created_at >= since,
                CreditLedger.entry_type == "charge",
            )
        )
        usd_cost = cost_result.scalar() or Decimal(0)

        # Requests by status
        status_stats = await self._db.execute(
            select(Request.status, func.count(Request.id))
            .where(Request.student_id == student_id, Request.created_at >= since)
            .group_by(Request.status)
        )
        status_breakdown = {row[0]: row[1] for row in status_stats}

        return {
            "student_id": str(student_id),
            "period_days": days,
            "total_requests": total_requests,
            "credits_consumed": float(credits),
            "usd_cost": float(cost_result.scalar() or Decimal(0)),
            "status_breakdown": status_breakdown,
        }

    async def get_provider_usage(self, days: int = 30) -> list[dict]:
        """Get usage breakdown by provider."""
        since = datetime.now() - timedelta(days=days)

        # This would require joining credit_ledger with model_configurations and providers
        # For now, return empty list - can be implemented with proper joins
        return []

    async def get_model_usage(self, days: int = 30) -> list[dict]:
        """Get usage breakdown by model."""
        since = datetime.now() - timedelta(days=days)

        # Similar - would need joins with model_configurations
        return []

    async def get_cost_trends(self, days: int = 30) -> list[dict]:
        """Get daily cost trends."""
        since = datetime.now() - timedelta(days=days)

        daily_costs = await self._db.execute(
            select(
                func.date(CreditLedger.created_at).label("date"),
                func.sum(CreditLedger.computed_usd_cost).label("usd_cost"),
                func.sum(CreditLedger.credits_charged).label("credits"),
            )
            .where(
                CreditLedger.created_at >= since,
                CreditLedger.entry_type == "charge",
            )
            .group_by(func.date(CreditLedger.created_at))
            .order_by(func.date(CreditLedger.created_at))
        )

        return [
            {
                "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                "usd_cost": float(row[1] or 0),
                "credits": float(row[2] or 0),
            }
            for row in daily_costs
        ]

    async def get_top_students(self, limit: int = 10, days: int = 30) -> list[dict]:
        """Get top students by credit consumption."""
        since = datetime.now() - timedelta(days=days)

        top_students = await self._db.execute(
            select(
                CreditLedger.student_id,
                func.sum(CreditLedger.credits_charged).label("credits"),
                func.sum(CreditLedger.computed_usd_cost).label("usd_cost"),
                func.count(CreditLedger.id).label("requests"),
            )
            .where(
                CreditLedger.created_at >= since,
                CreditLedger.entry_type == "charge",
            )
            .group_by(CreditLedger.student_id)
            .order_by(desc(func.sum(CreditLedger.credits_charged)))
            .limit(limit)
        )

        return [
            {
                "student_id": str(row[0]),
                "credits": float(row[1]),
                "usd_cost": float(row[1]),
                "requests": row[3],
            }
            for row in top_students
        ]