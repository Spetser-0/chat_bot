"""
app/api/v1/routes/health.py
─────────────────────────────
Health and readiness endpoints.
Readiness checks database connectivity.
Never exposes internal configuration or stack traces.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness() -> dict:
    """Kubernetes-style liveness probe. Always returns 200 if process is alive."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Readiness probe. Checks database connectivity.
    Returns 503 if the database is unreachable.
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

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    payload = {
        "status": "ready" if db_ok else "not_ready",
        "checks": {
            "database": {
                "status": "ok" if db_ok else "error",
                "latency_ms": latency_ms,
                **({"error": db_error} if db_error else {}),
            }
        },
        "version": settings.app_version,
    }

    if not db_ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=payload)

    return payload
