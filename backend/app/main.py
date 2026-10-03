"""
app/main.py
────────────
FastAPI application factory.
Configures middleware, exception handlers, CORS, and mounts the API router.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import SpetserError
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    configure_logging()
    logger = structlog.get_logger("spetser.startup")
    settings = get_settings()
    logger.info("Spetser AI starting", env=settings.app_env, version=settings.app_version)
    
    # Ensure database schema is created in development
    try:
        import app.models  # noqa
        from app.db.session import Base, get_engine
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully")
    except Exception as exc:
        logger.warning("Database initialization check skipped/failed", error=str(exc))
        
    yield
    logger.info("Spetser AI shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Spetser AI",
        description="Arabic-first academic AI platform — API",
        version=settings.app_version,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "Idempotency-Key"],
    )

    # ── Exception handlers ─────────────────────────────────────────────────
    from fastapi import HTTPException

    @app.exception_handler(SpetserError)
    async def spetser_error_handler(request: Request, exc: SpetserError) -> ORJSONResponse:
        logger = structlog.get_logger("spetser.errors")
        logger.warning(
            "Application error",
            error_code=exc.error_code,
            status=exc.http_status,
            # Never log exc.detail — may contain sensitive content
        )
        return ORJSONResponse(
            status_code=exc.http_status,
            content={
                "data": None,
                "error": {
                    "code": exc.error_code,
                    "message": exc.safe_message,
                },
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
        logger = structlog.get_logger("spetser.errors")
        logger.warning("HTTP exception", status_code=exc.status_code, detail=exc.detail)
        detail = exc.detail
        error_code = "HTTP_ERROR"
        message = "An error occurred"
        if isinstance(detail, dict) and "error" in detail:
            error_info = detail["error"]
            error_code = error_info.get("code", "HTTP_ERROR")
            message = error_info.get("message", "An error occurred")
        elif isinstance(detail, str):
            message = detail
        else:
            error_code = "HTTP_ERROR"
            message = str(detail)
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "error": {
                    "code": error_code,
                    "message": message,
                },
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        logger = structlog.get_logger("spetser.errors")
        logger.exception("Unhandled exception")
        return ORJSONResponse(
            status_code=500,
            content={
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.",
                },
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    # ── Routes ─────────────────────────────────────────────────────────────

    app.include_router(api_v1_router)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"service": "Spetser AI", "docs": "/api/docs"}

    return app


app = create_app()