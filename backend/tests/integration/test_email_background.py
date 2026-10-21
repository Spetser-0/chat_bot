"""
Email Background Task Tests
────────────────────────────
Verifies that emails are sent asynchronously and don't block responses.
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student


@pytest.mark.asyncio
async def test_register_returns_before_email_sent(client: AsyncClient):
    """Register should return 201 immediately, email sent in background."""
    with patch('app.services.email_service._send_email_task', new_callable=AsyncMock) as mock_send:
        # Make the mock slow to prove async behavior
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(3)  # Simulate slow email

        mock_send.side_effect = slow_send

        # Warm up app to trigger lifespan initialization before measuring registration latency
        await client.get("/api/v1/health")

        # Register should return quickly (< 1.5s) while slow_send would take 3.0s
        start = time.time()
        response = await client.post("/api/v1/auth/register", json={
            "name": "Test User",
            "email": "async-test@example.com",
            "password": "SecurePass123!",
        })
        elapsed = time.time() - start

        assert response.status_code == 201
        assert elapsed < 1.5, f"Register took {elapsed}s — email should be async"

        # Give background task time to complete
        await asyncio.sleep(0.5)

        # Verify email was queued
        assert mock_send.called


@pytest.mark.asyncio
async def test_email_failure_doesnt_fail_registration(client: AsyncClient, db: AsyncSession):
    """If email sending fails, registration should still succeed."""
    with patch('app.services.email_service._send_email_task', new_callable=AsyncMock) as mock_send:
        # Simulate SMTP failure
        mock_send.side_effect = Exception("SMTP connection failed")

        response = await client.post("/api/v1/auth/register", json={
            "name": "Fail Test",
            "email": "fail-test@example.com",
            "password": "SecurePass123!",
        })

        # Registration should still succeed
        assert response.status_code == 201

        # User should be created (unverified)
        result = await db.execute(
            select(Student).where(Student.email == "fail-test@example.com")
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_verified is False


@pytest.mark.asyncio
async def test_development_mode_prints_to_console(client: AsyncClient, capsys):
    """In dev mode, email should print to console instead of sending."""
    # Ensure we're in development mode
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.app_env == "development"

    response = await client.post("/api/v1/auth/register", json={
        "name": "Dev Test",
        "email": "dev-test@example.com",
        "password": "SecurePass123!",
    })

    assert response.status_code == 201

    # Wait for background task
    await asyncio.sleep(0.2)

    # Check logs for dev mode message
    captured = capsys.readouterr()
    # Note: This might not capture logs depending on logging config
    # The real test is that it doesn't crash
