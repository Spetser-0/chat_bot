"""
app/api/v1/routes/health.py
────────────────────────────
Health and readiness endpoints.
Readiness checks database, optional Redis, and active AI provider count.
Never exposes internal configuration, connection strings, or stack traces.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.metrics import get_metrics
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness() -> dict:
    """Kubernetes-style liveness probe. Always returns 200 if process is alive."""
    return {"status": "ok"}


async def _check_redis() -> dict:
    """Soft Redis check — readiness does not fail hard if Redis is down
    (rate limits fall back to memory per Lesson 10.1)."""
    settings = get_settings()
    if settings.rate_limit_backend != "redis":
        return {"status": "skipped", "reason": "rate_limit_backend_is_memory"}
    start = time.perf_counter()
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.ping()
        finally:
            await client.aclose()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {"status": "ok", "latency_ms": latency}
    except Exception:
        return {"status": "error", "error": "redis_unreachable"}


async def _check_active_providers(db: AsyncSession) -> dict:
    from app.models.ai_provider import AIProvider

    start = time.perf_counter()
    try:
        count = (await db.execute(
            select(func.count(AIProvider.id)).where(AIProvider.is_active.is_(True))
        )).scalar_one()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "ok",
            "active_count": int(count),
            "latency_ms": latency,
            **({} if count else {"warning": "no_active_ai_providers"}),
        }
    except Exception:
        return {"status": "error", "error": "provider_check_failed"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Readiness probe. Checks database (hard fail), Redis (soft), and
    active AI provider count (informational).
    Returns 503 only if the database is unreachable.
    """
    settings = get_settings()
    start = time.monotonic()
    db_ok = False
    db_error = None

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_error = "database_unreachable"

    db_latency = round((time.monotonic() - start) * 1000, 2)
    redis_check = await _check_redis()
    providers_check = await _check_active_providers(db) if db_ok else {"status": "skipped"}

    payload = {
        "status": "ready" if db_ok else "not_ready",
        "checks": {
            "database": {
                "status": "ok" if db_ok else "error",
                "latency_ms": db_latency,
                **({"error": db_error} if db_error else {}),
            },
            "redis": redis_check,
            "ai_providers": providers_check,
        },
        "version": settings.app_version,
    }

    if not db_ok:
        raise HTTPException(status_code=503, detail=payload)

    return payload


@router.get("/metrics")
async def public_metrics_snapshot() -> dict:
    """Lightweight operational counters (no auth — non-sensitive aggregates only).

    Detailed LLM cost / revenue analytics live under /admin/analytics.
    """
    snap = get_metrics().snapshot()
    # Strip per-status breakdowns that could reveal attack probing volume
    # if desired; for now only expose the top-level counters that are safe.
    counters = {
        k: v for k, v in snap["counters"].items()
        if not k.startswith("http_requests_total.")  # keep cardinality low
    }
    return {
        "uptime_seconds": snap["uptime_seconds"],
        "counters": counters,
        "histograms": {
            "http_request_latency_ms": snap["histograms"].get("http_request_latency_ms"),
            "llm_latency_ms": snap["histograms"].get("llm_latency_ms"),
        },
    }
