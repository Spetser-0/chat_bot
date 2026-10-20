"""
CORS Headers Test — P0.2
─────────────────────────
Verifies that:
1. Success responses include CORS headers for allowed origins.
2. Error responses (4xx) ALSO include CORS headers.
3. Preflight OPTIONS requests succeed with the Authorization header.
4. Disallowed origins never receive Access-Control-Allow-Origin.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.fixture
def allowed_origin() -> str:
    return get_settings().allowed_origins_list[0]


@pytest.mark.asyncio
async def test_success_response_has_cors_headers(client: AsyncClient, allowed_origin: str) -> None:
    response = await client.get("/api/v1/health/live", headers={"Origin": allowed_origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_error_response_has_cors_headers(client: AsyncClient, allowed_origin: str) -> None:
    """This was the P0.2 bug — the 404 rewrite runs outside CORSMiddleware."""
    response = await client.get(
        "/api/v1/nonexistent-route-404", headers={"Origin": allowed_origin}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.headers.get("access-control-allow-origin") == allowed_origin, (
        "Error responses must include CORS headers so the browser can read the error body"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_unauthorized_error_has_cors_headers(client: AsyncClient, allowed_origin: str) -> None:
    """Handler-produced 401s must also be readable cross-origin."""
    response = await client.get("/api/v1/credits/balance", headers={"Origin": allowed_origin})
    assert response.status_code == 401
    assert response.headers.get("access-control-allow-origin") == allowed_origin
    body = response.json()
    assert body["data"] is None and body["error"] is not None and "request_id" in body


@pytest.mark.asyncio
async def test_preflight_allows_authorization(client: AsyncClient, allowed_origin: str) -> None:
    """API key / Bearer auth preflight must succeed."""
    response = await client.options(
        "/api/v1/chat/completions",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert response.status_code == 200
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "x-api-key" in allow_headers


@pytest.mark.asyncio
async def test_disallowed_origin_rejected(client: AsyncClient) -> None:
    for path in ("/api/v1/health/live", "/api/v1/nonexistent-route-404"):
        response = await client.get(path, headers={"Origin": "https://evil.example.com"})
        assert response.headers.get("access-control-allow-origin") is None, path
