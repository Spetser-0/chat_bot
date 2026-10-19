"""
backend/tests/test_password_reset.py
────────────────────────────────────
Tests for Forgot Password Flow (OTP verification and password reset).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.student import Student
from app.services.verification_service import VerificationService


@pytest.mark.asyncio
async def test_forgot_password_generic_response(client: AsyncClient, student: Student):
    """Test that /forgot-password returns success for both existing and non-existing emails."""
    # Existing user
    resp1 = await client.post("/api/v1/auth/forgot-password", json={"email": student.email})
    assert resp1.status_code == 200

    # Non-existing user
    resp2 = await client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent_reset@example.com"})
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_verify_reset_code_with_wrong_code(client: AsyncClient, student: Student):
    """Test that invalid reset code is rejected."""
    await client.post("/api/v1/auth/forgot-password", json={"email": student.email})

    response = await client.post(
        "/api/v1/auth/verify-reset-code",
        json={"email": student.email, "code": "000000"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_full_password_reset_flow(client: AsyncClient, db: AsyncSession, student: Student):
    """Test end-to-end forgot password flow: request -> verify -> reset -> login."""
    original_pass = "password123"
    new_pass = "BrandNewPassword123!"

    # 1. Request reset
    await client.post("/api/v1/auth/forgot-password", json={"email": student.email})

    # 2. Set known OTP code on user in DB
    test_otp = "654321"
    result = await db.execute(select(Student).where(Student.email == student.email))
    s = result.scalar_one()
    s.verification_code = VerificationService._hash_code(test_otp)
    await db.commit()

    # 3. Verify OTP code and get reset token
    verify_resp = await client.post(
        "/api/v1/auth/verify-reset-code",
        json={"email": student.email, "code": test_otp},
    )
    assert verify_resp.status_code == 200
    reset_token = verify_resp.json()["reset_token"]
    assert reset_token is not None

    # 4. Reset password
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"reset_token": reset_token, "new_password": new_pass},
    )
    assert reset_resp.status_code == 200

    # 5. Old password no longer works
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": student.email, "password": original_pass},
    )
    assert old_login.status_code == 401

    # 6. New password works successfully
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": student.email, "password": new_pass},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_with_invalid_token(client: AsyncClient):
    """Test that resetting with invalid token is rejected."""
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"reset_token": "fake.invalid.token", "new_password": "NewPassword123!"},
    )
    assert response.status_code == 422
