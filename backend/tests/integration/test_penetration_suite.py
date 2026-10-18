"""
tests/integration/test_penetration_suite.py
───────────────────────────────────────────
Automated penetration testing suite based on Phase 5 of spets.md:
- Test 1: Wrong password login (401)
- Test 2: Access protected endpoint without token (401)
- Test 3: Access protected endpoint with invalid token (401)
- Test 4: Access admin endpoint with regular user token (403)
- Test 5: XSS input handling in chat message
- Test 6: SQL Injection attempt in login (401)
- Test 7: Extremely long input exceeds validation limits (422)
- Test 8: Rate limiting triggers on rapid requests (429)
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.models.student import Student
from app.services.auth import SESSION_COOKIE_NAME, create_session_token, hash_password


@pytest_asyncio.fixture
async def regular_student(db) -> Student:
    s = Student(
        id=uuid.uuid4(),
        email=f"pentest_user_{uuid.uuid4().hex[:6]}@example.com",
        display_name="Pentest Student",
        password_hash=hash_password("ValidPassword123!"),
        role="student",
        status="active",
        credit_balance=100,
    )
    db.add(s)
    await db.commit()
    return s


@pytest_asyncio.fixture
async def unauth_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def student_client(app: FastAPI, regular_student: Student) -> AsyncGenerator[AsyncClient, None]:
    token = create_session_token(regular_student.id, regular_student.role)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={SESSION_COOKIE_NAME: token},
    ) as c:
        yield c


class TestPenetrationAuth:
    @pytest.mark.asyncio
    async def test_1_wrong_password_login_returns_401(self, unauth_client: AsyncClient, regular_student: Student):
        resp = await unauth_client.post(
            "/api/v1/auth/login",
            json={"email": regular_student.email, "password": "DefinitelyWrongPassword123!"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_2_protected_endpoint_without_token_returns_401(self, unauth_client: AsyncClient):
        resp = await unauth_client.get("/api/v1/conversations")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_3_protected_endpoint_with_invalid_token_returns_401(self, unauth_client: AsyncClient):
        unauth_client.cookies.set(SESSION_COOKIE_NAME, "tampered.invalid.token.signature")
        resp = await unauth_client.get("/api/v1/conversations")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_4_regular_user_on_admin_endpoint_returns_403(self, student_client: AsyncClient):
        resp = await student_client.get("/api/v1/admin/users")
        assert resp.status_code == 403


class TestPenetrationInputValidation:
    @pytest.mark.asyncio
    async def test_5_xss_injection_attempt_is_safely_handled(self, student_client: AsyncClient):
        # Send raw script injection
        resp = await student_client.post(
            "/api/v1/chat/completions",
            json={
                "message": "<script>alert('XSS')</script> Hello Spetser!",
                "stream": False,
            },
        )
        # Should succeed or return validation error, never execute or leak executable payload
        assert resp.status_code in (200, 422, 502)
        if resp.status_code == 200:
            data = resp.json()
            assert "<script>" not in data.get("content", "") or "&lt;script&gt;" in data.get("content", "")

    @pytest.mark.asyncio
    async def test_6_sql_injection_in_login_returns_401(self, unauth_client: AsyncClient):
        resp = await unauth_client.post(
            "/api/v1/auth/login",
            json={"email": 'admin@spetser.ai" OR "1"="1', "password": "arbitrary_password"},
        )
        assert resp.status_code in (401, 422)
        assert resp.status_code != 200

    @pytest.mark.asyncio
    async def test_7_oversized_input_rejected_with_422(self, student_client: AsyncClient):
        huge_message = "A" * 100001
        resp = await student_client.post(
            "/api/v1/chat/completions",
            json={"message": huge_message, "stream": False},
        )
        assert resp.status_code == 422


class TestPenetrationRateLimiting:
    @pytest.mark.asyncio
    async def test_8_rapid_requests_throttling(self, unauth_client: AsyncClient):
        # Test auth rate limit (5/min on login)
        hit_429 = False
        for _ in range(12):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@example.com", "password": "Password123!"},
            )
            if resp.status_code == 429:
                hit_429 = True
                break

        assert hit_429, "Expected 429 Too Many Requests on rapid login attempts"
