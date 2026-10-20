"""
API Contract Test — P0.1
─────────────────────────
Every JSON response from /api/v1/* MUST be wrapped in the standard envelope:
    {"data": <payload>, "error": null, "request_id": "<uuid>"}

Exceptions:
- SSE/streaming responses (text/event-stream) are NOT wrapped.
- Error responses already follow the envelope (Lesson 10.4).

This test FAILS on commit 61e8a38 and MUST pass after the fix.
"""
import pytest
from httpx import AsyncClient

# All read endpoints that return JSON (not SSE)
CONTRACT_ROUTES = [
    "/api/v1/conversations",
    "/api/v1/credits/balance",
    "/api/v1/credits/history",
    "/api/v1/skills",
    "/api/v1/referrals/me",
    "/api/v1/health/live",
    "/api/v1/health/ready",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", CONTRACT_ROUTES)
async def test_success_response_uses_envelope(
    authenticated_client: AsyncClient,
    route: str,
) -> None:
    """Every successful JSON response must follow {data, error, request_id}."""
    response = await authenticated_client.get(route)
    
    # Skip 4xx — errors already have the envelope (Lesson 10.4)
    if response.status_code >= 400:
        pytest.skip(f"{route} returned {response.status_code}")
    
    # Skip SSE streams (different content-type)
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        pytest.skip("SSE stream — exempt from envelope")
    
    assert "application/json" in content_type, (
        f"{route}: expected JSON, got {content_type}"
    )
    
    body = response.json()
    assert isinstance(body, dict), (
        f"{route}: envelope must be a dict, got {type(body).__name__}. "
        f"Bare arrays break the frontend extractData() function."
    )
    assert "data" in body, f"{route}: missing 'data' field"
    assert "error" in body, f"{route}: missing 'error' field"
    assert "request_id" in body, f"{route}: missing 'request_id' field"
    assert body["error"] is None, f"{route}: success must have error=null"


@pytest.mark.asyncio
async def test_error_response_uses_envelope(authenticated_client: AsyncClient) -> None:
    """Error responses must also follow the envelope (regression guard)."""
    response = await authenticated_client.get(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["error"] is not None
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "request_id" in body
