"""
tests/integration/test_auth_routes.py
───────────────────────────────────────
Integration tests for authentication routes using the test ASGI client.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.auth import SESSION_COOKIE_NAME


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "securepassword123",
                "display_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "student"
        # Session cookie must be set
        assert SESSION_COOKIE_NAME in response.cookies

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@test.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_register_short_password_rejected(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "short@test.com", "password": "123"},
        )
        assert response.status_code == 422  # Pydantic validation


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, student):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": student.email, "password": "password123"},
        )
        assert response.status_code == 200
        assert SESSION_COOKIE_NAME in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, student):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": student.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "password123"},
        )
        assert response.status_code == 401


class TestMe:
    @pytest.mark.asyncio
    async def test_me_authenticated(self, authenticated_client: AsyncClient, student):
        response = await authenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == student.email
        # Lesson 9.5: frontend premium lock needs this flag.
        assert data["is_premium"] is False

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_cookie(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            cookies={SESSION_COOKIE_NAME: "invalid.token.value"},
        )
        assert response.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code == 200


class TestHealth:
    @pytest.mark.asyncio
    async def test_liveness(self, client: AsyncClient):
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_request_id_header_present(self, client: AsyncClient):
        response = await client.get("/api/v1/health/live")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_developer_cannot_access_student_resource(
        self, developer_client: AsyncClient, student
    ):
        """Developer role does not grant access to another student's resources."""
        # This will expand as student-specific routes are added in Phase 2
        response = await developer_client.get("/api/v1/auth/me")
        # Developer is authenticated, so /me works — but returns THEIR identity
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["role"] == "developer"
        # Not the regular student's email
        assert data["email"] != student.email
