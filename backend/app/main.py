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
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_v1_router
from app.api.v1.routes.auth import limiter as auth_limiter
from app.core.config import get_settings
from app.core.cors import (
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_EXPOSE_HEADERS,
    attach_cors_headers,
    request_id_of,
)
from app.core.errors import SpetserError
from app.core.logging import configure_logging
from app.core.metrics import get_metrics
from app.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    configure_logging()
    logger = structlog.get_logger("spetser.startup")
    settings = get_settings()
    logger.info("Spetser AI starting", env=settings.app_env, version=settings.app_version)

    # Rate-limit store (memory or Redis per RATE_LIMIT_BACKEND).
    from app.core.rate_limit import close_rate_limit_store, init_redis_store
    await init_redis_store()

    # Schema changes are applied by Alembic; create_all is development-only.
    if settings.is_development:
        try:
            import app.models  # noqa
            from app.db.session import Base, get_engine
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Development database schema initialized")
        except Exception:
            logger.warning("Development database initialization skipped")

        # Auto-promote the configured developer account to developer role.
        try:
            from sqlalchemy import select
            from app.models.student import Student
            from app.db.session import get_session_factory

            factory = get_session_factory()
            async with factory() as db:
                result = await db.execute(
                    select(Student).where(Student.email == settings.developer_email)
                )
                dev = result.scalar_one_or_none()
                if dev and dev.role != "developer":
                    dev.role = "developer"
                    await db.commit()
                    logger.info("Developer account promoted", email=dev.email)
                elif dev:
                    logger.info("Developer account already configured", email=dev.email)
                else:
                    logger.warning(
                        "Developer email not found in database — register it first",
                        email=settings.developer_email,
                    )
        except Exception as exc:
            logger.warning("Developer role assignment failed", error=str(exc))

    yield
    await close_rate_limit_store()
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
    app.state.limiter = auth_limiter
    app.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: attach_cors_headers(request, ORJSONResponse(
            status_code=429,
            content={
                "data": None,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "محاولات كثيرة. حاول لاحقاً.",
                },
                "request_id": request_id_of(request),
            },
            headers={"Retry-After": "60"},
        )),
    )
    app.add_middleware(SlowAPIMiddleware)

    # Distributed rate limiter (Phase 4)
    from app.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=100,
        window_seconds=60,
    )

    # ── Middleware ─────────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)

    @app.middleware("http")
    async def request_metrics(request: Request, call_next):
        """Record per-request counters and latency (Phase 11, Lesson 11.1)."""
        import time as _time

        start = _time.perf_counter()
        response = await call_next(request)
        latency_ms = (_time.perf_counter() - start) * 1000
        # Prefer the matched route path when available to avoid high-cardinality paths.
        route = request.scope.get("route")
        path = getattr(route, "path", None) or request.url.path
        get_metrics().record_request(
            method=request.method,
            path=path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        return response

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
    @app.middleware("http")
    async def envelope_success_responses(request: Request, call_next) -> Response:
        """
        Wrap successful JSON responses from /api/v1/* in the standard envelope:
            {"data": <payload>, "error": null, "request_id": "<uuid>"}
        
        Exemptions (pass-through unchanged):
            - Non-/api/v1/ paths (health probes, webhooks, etc. if needed)
            - Non-2xx status codes (errors are wrapped by exception handlers)
            - SSE / streaming responses (content-type: text/event-stream)
            - Non-JSON responses (downloads, binary)
        """
        import json as _json
        from starlette.responses import Response

        response = await call_next(request)

        path = request.url.path
        is_api = path.startswith("/api/v1/")
        is_success = 200 <= response.status_code < 300
        content_type = response.headers.get("content-type", "")
        is_json = "application/json" in content_type
        is_stream = "text/event-stream" in content_type

        if not (is_api and is_success and is_json and not is_stream):
            return response

        # Read the body bytes. StreamingResponse / SSE already bypassed above.
        body_chunks = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                body_chunks.append(chunk.encode("utf-8"))
            else:
                body_chunks.append(chunk)
        raw_bytes = b"".join(body_chunks)

        try:
            raw_payload = _json.loads(raw_bytes)
        except _json.JSONDecodeError:
            # Non-JSON content-type lied — pass through
            return Response(
                content=raw_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )

        request_id = getattr(request.state, "request_id", None) or response.headers.get("X-Request-ID")

        # Preserve original headers (except content-length, which we must recalc)
        new_headers = {k: v for k, v in response.headers.items()
                       if k.lower() != "content-length"}

        # Avoid double-wrapping if the endpoint already returned an envelope
        if isinstance(raw_payload, dict) and "data" in raw_payload and "error" in raw_payload:
            if raw_payload.get("request_id") is None:
                raw_payload["request_id"] = request_id
            return ORJSONResponse(
                content=raw_payload,
                status_code=response.status_code,
                headers=new_headers,
            )

        wrapped = {
            "data": raw_payload,
            "error": None,
            "request_id": request_id,
        }

        return ORJSONResponse(
            content=wrapped,
            status_code=response.status_code,
            headers=new_headers,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,  # P0.2: includes Authorization + X-API-Key
        expose_headers=CORS_EXPOSE_HEADERS,
        max_age=600,
    )

    # ── Exception handlers ─────────────────────────────────────────────────
    from fastapi import HTTPException

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        """Pydantic body/query validation → consistent Arabic envelope (Lesson 10.4).

        Never echo raw input back to the client (could reflect secrets or
        injection payloads); only field paths and short messages.
        """
        logger = structlog.get_logger("spetser.errors")
        logger.warning(
            "Request validation failed",
            errors=[{"loc": list(e.get("loc", ())), "type": e.get("type", "")} for e in exc.errors()],
        )
        # Prefer the first human-readable message; fall back to generic Arabic.
        message = "البيانات المُرسلة غير صحيحة."
        for e in exc.errors():
            msg = e.get("msg", "")
            if msg and not msg.startswith("Value error, "):
                message = msg
                break
            if msg.startswith("Value error, "):
                message = msg[len("Value error, "):]
                break
        return attach_cors_headers(request, ORJSONResponse(
            status_code=422,
            content={
                "data": None,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "details": [
                        {"loc": list(e.get("loc", ())), "type": e.get("type", "")}
                        for e in exc.errors()[:10]
                    ],
                },
                "request_id": request_id_of(request),
            },
        ))

    from app.core.exceptions import AppException, app_exception_handler
    app.add_exception_handler(AppException, app_exception_handler)

    @app.exception_handler(SpetserError)
    async def spetser_error_handler(request: Request, exc: SpetserError) -> ORJSONResponse:
        logger = structlog.get_logger("spetser.errors")
        logger.warning(
            "Application error",
            error_code=exc.error_code,
            status=exc.http_status,
            # Never log exc.detail — may contain sensitive content
        )
        return attach_cors_headers(request, ORJSONResponse(
            status_code=exc.http_status,
            content={
                "data": None,
                "error": {
                    "code": exc.error_code,
                    "message": exc.safe_message,
                },
                "request_id": request_id_of(request),
            },
        ))

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
        logger = structlog.get_logger("spetser.errors")
        logger.warning("HTTP exception", status_code=exc.status_code)
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
        return attach_cors_headers(request, ORJSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "error": {
                    "code": error_code,
                    "message": message,
                },
                "request_id": request_id_of(request),
            },
            headers=getattr(exc, "headers", None),
        ))

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        logger = structlog.get_logger("spetser.errors")
        logger.exception("Unhandled exception")
        return attach_cors_headers(request, ORJSONResponse(
            status_code=500,
            content={
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.",
                },
                "request_id": request_id_of(request),
            },
        ))

    # ── Routes ─────────────────────────────────────────────────────────────

    app.include_router(api_v1_router)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"service": "Spetser AI", "docs": "/api/docs"}

    # Unmatched paths: Starlette returns a bare 404 without our envelope.
    # Mount a catch-all so every miss uses the global error shape (Lesson 10.4).
    @app.middleware("http")
    async def unify_not_found(request: Request, call_next):
        # Registered after CORSMiddleware → runs OUTSIDE it, so CORS headers
        # must be attached explicitly (P0.2).
        response = await call_next(request)
        if response.status_code == 404 and request.url.path.startswith("/api/"):
            return attach_cors_headers(request, ORJSONResponse(
                status_code=404,
                content={
                    "data": None,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "المورد المطلوب غير موجود.",
                    },
                    "request_id": request_id_of(request),
                },
                headers={"X-Request-ID": rid} if (rid := request_id_of(request)) else None,
            ))
        return response

    return app


app = create_app()
