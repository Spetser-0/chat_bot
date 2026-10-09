"""
app/api/v1/routes/admin/metrics.py
───────────────────────────────────
Runtime process metrics for operators (Phase 11, Lesson 11.3).

Read-only. Developer+ only. No secrets, no PII — counters and latency
summaries only. Business analytics stay under /admin/analytics.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_developer
from app.core.metrics import get_metrics
from app.models.student import Student

router = APIRouter(prefix="/admin/metrics", tags=["Admin - Metrics"])


@router.get("")
async def runtime_metrics(_: Student = Depends(get_developer)) -> dict:
    """Full in-process metrics snapshot (counters, gauges, histograms)."""
    return get_metrics().snapshot()


@router.post("/reset", status_code=204)
async def reset_metrics(_: Student = Depends(get_developer)) -> None:
    """Clear in-process counters (ops only; does not touch the database)."""
    get_metrics().reset()
