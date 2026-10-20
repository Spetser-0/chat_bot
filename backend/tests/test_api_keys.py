"""
backend/tests/test_api_keys.py
───────────────────────────────
Tests for Developer Panel API key lifecycle, verification, and endpoints.
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.services.api_key_service import api_key_service


@pytest.mark.asyncio
async def test_create_api_key_as_developer(developer_client: AsyncClient, db: AsyncSession):
    """Test that a developer/admin can create a new API key."""
    response = await developer_client.post(
        "/api/v1/developer/api-keys",
        json={
            "name": "Production Bot Key",
            "system_prompt": "You are a helpful math tutor.",
            "max_credits_per_day": 500,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Production Bot Key"
    assert data["system_prompt"] == "You are a helpful math tutor."
    assert data["max_credits_per_day"] == 500
    assert data["is_active"] is True
    assert "plain_key" in data
    assert data["plain_key"].startswith("sk-spetser-")
    assert data["key_prefix"].startswith("sk-spetser-")

    # In DB, plain key is NOT stored; only hash
    result = await db.execute(select(APIKey).where(APIKey.id == uuid.UUID(data["id"])))
    key_in_db = result.scalar_one_or_none()
    assert key_in_db is not None
    assert key_in_db.key_hash != data["plain_key"]


@pytest.mark.asyncio
async def test_regular_student_cannot_access_developer_keys(authenticated_client: AsyncClient):
    """Test that regular students are forbidden from developer panel."""
    response = await authenticated_client.get("/api/v1/developer/api-keys")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_and_update_api_key(developer_client: AsyncClient):
    """Test listing and updating API key attributes."""
    # 1. Create
    create_res = await developer_client.post(
        "/api/v1/developer/api-keys",
        json={"name": "Initial Key", "max_credits_per_day": 100},
    )
    assert create_res.status_code == 201
    key_id = create_res.json()["id"]

    # 2. List
    list_res = await developer_client.get("/api/v1/developer/api-keys")
    assert list_res.status_code == 200
    keys = list_res.json()["data"]
    assert any(k["id"] == key_id for k in keys)


    # 3. Update
    patch_res = await developer_client.patch(
        f"/api/v1/developer/api-keys/{key_id}",
        json={
            "name": "Updated Key Name",
            "is_active": False,
            "system_prompt": "Custom updated prompt",
        },
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["name"] == "Updated Key Name"
    assert updated_data["is_active"] is False
    assert updated_data["system_prompt"] == "Custom updated prompt"


@pytest.mark.asyncio
async def test_regenerate_api_key(developer_client: AsyncClient, db: AsyncSession):
    """Test regenerating an existing API key."""
    # 1. Create key
    create_res = await developer_client.post(
        "/api/v1/developer/api-keys",
        json={"name": "Regen Key"},
    )
    key_id = create_res.json()["id"]
    old_plain = create_res.json()["plain_key"]

    # Verify old key works in service
    verified_old = await api_key_service.verify_key(db, old_plain)
    assert verified_old is not None
    assert verified_old.total_requests == 1

    # 2. Regenerate
    regen_res = await developer_client.post(f"/api/v1/developer/api-keys/{key_id}/regenerate")
    assert regen_res.status_code == 200
    new_plain = regen_res.json()["plain_key"]
    assert new_plain != old_plain

    # Old key is now invalid
    assert await api_key_service.verify_key(db, old_plain) is None

    # New key is valid
    verified_new = await api_key_service.verify_key(db, new_plain)
    assert verified_new is not None


@pytest.mark.asyncio
async def test_delete_api_key(developer_client: AsyncClient, db: AsyncSession):
    """Test deleting an API key."""
    create_res = await developer_client.post(
        "/api/v1/developer/api-keys",
        json={"name": "To Delete"},
    )
    key_id = create_res.json()["id"]

    del_res = await developer_client.delete(f"/api/v1/developer/api-keys/{key_id}")
    assert del_res.status_code == 200

    result = await db.execute(select(APIKey).where(APIKey.id == uuid.UUID(key_id)))
    assert result.scalar_one_or_none() is None
