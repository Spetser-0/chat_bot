"""
backend/tests/test_settings.py
──────────────────────────────
Tests for System Settings & Default Credits Control (Feature 5).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.services.settings_service import settings_service


@pytest.mark.asyncio
async def test_get_and_update_settings(developer_client: AsyncClient, db: AsyncSession):
    """Test reading and updating system settings by admin/developer."""
    # 1. Read default settings
    get_res = await developer_client.get("/api/v1/admin/settings")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "default_new_user_credits" in data
    assert data["default_new_user_credits"] >= 0

    # 2. Update default_new_user_credits to 500
    patch_res = await developer_client.patch(
        "/api/v1/admin/settings",
        json={"default_new_user_credits": 500},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["default_new_user_credits"] == 500

    # Verify from DB
    persisted = await settings_service.get_settings(db)
    assert persisted.default_new_user_credits == 500


@pytest.mark.asyncio
async def test_new_user_receives_configured_default_credits(
    developer_client: AsyncClient,
    client: AsyncClient,
    db: AsyncSession,
):
    """Test that newly registered students receive dynamically configured default credits."""
    # 1. Admin sets default credits to 750
    await developer_client.patch(
        "/api/v1/admin/settings",
        json={"default_new_user_credits": 750},
    )

    # 2. New student registers
    email = "dynamic_credits_student@test.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "ValidPassword123!",
            "display_name": "Credits Tester",
        },
    )
    assert reg_res.status_code == 201

    # 3. Verify user's credit balance in database matches configured 750
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()
    assert student is not None
    assert student.credit_balance == 750.0


@pytest.mark.asyncio
async def test_regular_student_cannot_modify_settings(authenticated_client: AsyncClient):
    """Test that regular students cannot read or modify admin settings."""
    res_get = await authenticated_client.get("/api/v1/admin/settings")
    assert res_get.status_code == 403

    res_patch = await authenticated_client.patch(
        "/api/v1/admin/settings",
        json={"default_new_user_credits": 1000},
    )
    assert res_patch.status_code == 403
