"""
app/core/cors.py
────────────────
CORS header injection helper for exception handlers (P0.2).

FastAPI's CORSMiddleware sits *inside* ServerErrorMiddleware, and any
``@app.middleware("http")`` registered after CORSMiddleware sits *outside* it.
Responses produced at those layers (generic 500 handler, 404 rewrite) never
pass through CORSMiddleware and lose their CORS headers — the browser then
hides the real error body behind an opaque CORS failure.

This helper restores the headers on every error response. It is idempotent:
calling it on a response that CORSMiddleware will also process is harmless.

Usage:
    return attach_cors_headers(request, ORJSONResponse(...))
"""
from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

#: Headers the browser is allowed to read from cross-origin responses.
CORS_EXPOSE_HEADERS: list[str] = [
    "X-Request-ID",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "Retry-After",
]

#: Request headers the browser may send on cross-origin requests.
CORS_ALLOW_HEADERS: list[str] = [
    "Content-Type",
    "X-Request-ID",
    "Idempotency-Key",
    "Authorization",  # Bearer + API-key auth preflight
    "X-API-Key",
    "Accept",
    "Accept-Language",
]

CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def attach_cors_headers(request: Request, response: Response) -> Response:
    """Attach CORS headers to ``response`` if the request origin is allowed."""
    origin = request.headers.get("origin")
    if not origin or origin not in get_settings().allowed_origins_list:
        return response

    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = ", ".join(CORS_EXPOSE_HEADERS)

    vary = response.headers.get("Vary")
    if not vary:
        response.headers["Vary"] = "Origin"
    elif "origin" not in vary.lower():
        response.headers["Vary"] = f"{vary}, Origin"
    return response


def request_id_of(request: Request) -> str | None:
    """Return the correlation ID set by RequestIDMiddleware (or the inbound header)."""
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
