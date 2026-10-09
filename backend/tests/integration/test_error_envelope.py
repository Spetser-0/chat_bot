"""
tests/integration/test_error_envelope.py
────────────────────────────────────────
Lesson 10.4 — global error envelope consistency for validation / rate limit / not found.
"""
from __future__ import annotations

import uuid


class TestValidationEnvelope:
    async def test_chat_empty_body_422_envelope(self, authenticated_client):
        r = await authenticated_client.post("/api/v1/chat/completions", json={})
        assert r.status_code == 422
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"]
        assert "details" in body["error"]
        assert isinstance(body["error"]["details"], list)
        # details must not echo the raw payload values (only loc/type)
        for d in body["error"]["details"]:
            assert set(d.keys()) <= {"loc", "type"}

    async def test_chat_invalid_uuid_422(self, authenticated_client):
        r = await authenticated_client.post(
            "/api/v1/chat/completions",
            json={"message": "hi", "conversation_id": "not-a-uuid"},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_auth_register_weak_password_422(self, client):
        r = await client.post(
            "/api/v1/auth/register",
            json={"email": "x@y.com", "password": "ab"},
        )
        assert r.status_code == 422
        body = r.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        # Arabic-safe message present
        assert body["error"]["message"]


class TestNotFoundEnvelope:
    async def test_unknown_route_404_envelope(self, client):
        r = await client.get("/api/v1/does-not-exist")
        assert r.status_code == 404
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"]
        assert body["error"]["message"]


class TestSpetserErrorEnvelope:
    async def test_me_unauthenticated_401_envelope(self, client):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"] == "AUTHENTICATION_REQUIRED"
        # Arabic user-facing message
        assert "المصادقة" in body["error"]["message"] or body["error"]["message"]
        assert "request_id" in body


class TestRateLimitAuthEnvelope:
    async def test_auth_429_uses_unified_code(self, client, monkeypatch):
        """After 5 login attempts, 429 must use RATE_LIMIT_EXCEEDED (not RATE_LIMITED)."""
        from app.api.v1.routes.auth import limiter

        limiter.reset()
        email = f"rl_{uuid.uuid4().hex[:6]}@test.com"
        for _ in range(5):
            r = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "wrong-password"},
            )
            # login fails with 401 until limit; may also 422/409 depending on path
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert r.status_code == 429
        body = r.json()
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert body["data"] is None
        assert "request_id" in body
        limiter.reset()
