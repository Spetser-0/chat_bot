"""
backend/tests/test_verification.py
───────────────────────────────────
Tests for Email Verification with OTP during account registration.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.services.verification_service import verification_service


@pytest.mark.asyncio
async def test_register_creates_unverified_user(client: AsyncClient, db: AsyncSession):
    """Test that registration creates an unverified account and initiates OTP."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "unverified_test@example.com",
            "password": "SecurePassword123!",
            "display_name": "Unverified User",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["requires_verification"] is True

    # Verify user in database is not verified
    result = await db.execute(select(Student).where(Student.email == "unverified_test@example.com"))
    student = result.scalar_one_or_none()
    assert student is not None
    assert student.is_verified is False
    assert student.verification_code is not None
    assert student.verification_expires_at is not None
    assert student.verification_attempts == 0


@pytest.mark.asyncio
async def test_login_blocked_for_unverified_user(client: AsyncClient):
    """Test that login is blocked for unverified accounts."""
    # 1. Register account
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked_login@example.com",
            "password": "SecurePassword123!",
            "display_name": "Blocked User",
        },
    )

    # 2. Try to log in
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "blocked_login@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 401
    assert "غير مفعّل" in response.json()["error"]["message"] or "email" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_verify_with_wrong_code_fails(client: AsyncClient, db: AsyncSession):
    """Test that entering a wrong code increments attempts and fails."""
    # 1. Register account
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong_code@example.com",
            "password": "SecurePassword123!",
            "display_name": "Wrong Code User",
        },
    )

    # 2. Send invalid code
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "wrong_code@example.com",
            "code": "000000",
        },
    )
    assert response.status_code == 422

    # Check attempts incremented
    result = await db.execute(select(Student).where(Student.email == "wrong_code@example.com"))
    student = result.scalar_one()
    assert student.verification_attempts == 1
    assert student.is_verified is False


@pytest.mark.asyncio
async def test_verify_with_correct_code_succeeds(client: AsyncClient, db: AsyncSession):
    """Test that entering the correct code activates the account and allows login."""
    email = "success_verify@example.com"
    password = "SecurePassword123!"

    # 1. Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Success User",
        },
    )

    # 2. Extract or generate known OTP for this user
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one()
    test_otp = "123456"
    student.verification_code = verification_service._hash_code(test_otp)
    await db.commit()

    # 3. Verify with correct OTP
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": email,
            "code": test_otp,
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_verified"] is True

    # 4. Check user state in DB
    await db.refresh(student)
    assert student.is_verified is True
    assert student.verification_code is None
    assert student.verification_expires_at is None

    # 5. Now user can log in successfully
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_resend_code_succeeds(client: AsyncClient, db: AsyncSession):
    """Test that requesting a new code resets attempts and updates expiration."""
    email = "resend_test@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "display_name": "Resend User"},
    )

    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one()
    original_code_hash = student.verification_code

    # Resend code
    response = await client.post(
        "/api/v1/auth/resend-code",
        json={"email": email},
    )
    assert response.status_code == 200

    await db.refresh(student)
    assert student.verification_code is not None
    assert student.verification_attempts == 0


@pytest.mark.asyncio
async def test_expired_code_rejected(client: AsyncClient, db: AsyncSession):
    """Test that expired verification code cannot be used."""
    email = "expired_test@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "display_name": "Expired User"},
    )

    # Set expiration in past
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one()
    student.verification_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    test_otp = "888999"
    student.verification_code = verification_service._hash_code(test_otp)
    await db.commit()

    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": test_otp},
    )
    assert response.status_code == 422
    assert "انتهت صلاحية" in response.json()["error"]["message"] or "expired" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_max_attempts_exceeded_blocks_code(client: AsyncClient, db: AsyncSession):
    """Test that exceeding max attempts blocks further verification until resend."""
    email = "max_attempts@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "display_name": "Max Attempts User"},
    )

    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one()
    student.verification_attempts = 5
    await db.commit()

    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": "123456"},
    )
    assert response.status_code == 401
    assert "تجاوزت الحد الأقصى" in response.json()["error"]["message"] or "too many" in response.json()["error"]["message"].lower()
