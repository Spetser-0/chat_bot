"""
Brevo HTTP API & Email Provider Unit Tests
──────────────────────────────────────────
Tests transactional email sending via Brevo HTTPS API, provider precedence,
error handling, and secrecy in logs.
"""
import json
import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.email_service import (
    _mask_email,
    _send_email_task,
    _send_via_brevo,
)


def test_mask_email_privacy():
    """Verify email masking for audit log privacy."""
    assert _mask_email("student@example.com") == "s***@example.com"
    assert _mask_email("a@domain.org") == "a***@domain.org"
    assert _mask_email("someone@gmail.com") == "s***@gmail.com"
    assert _mask_email("invalid-email") == "***"


@pytest.mark.asyncio
async def test_brevo_success_201(monkeypatch, caplog):
    """(a) Status 201 should succeed without raising, log info with messageId and masked email."""
    test_key = "xkeysib-supersecret-test-key-12345"
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: Settings(
            app_secret_key="x" * 32,
            session_secret_key="y" * 32,
            brevo_api_key=test_key,
            brevo_sender_name="Spetser AI",
            smtp_from="noreply@spetser.ai",
        ),
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=201,
            json={"messageId": "<20261022.mock-message-id@brevo>"},
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with caplog.at_level(logging.INFO, logger="spetser.email"):
            await _send_via_brevo(
                to_email="student@university.edu",
                subject="رمز التحقق",
                html_body="<p>123456</p>",
                client=client,
            )

    # Key must NOT be leaked in logs
    assert test_key not in caplog.text
    # Masked recipient should be present
    assert "s***@university.edu" in caplog.text
    # Raw email should NOT be present in log output
    assert "student@university.edu" not in caplog.text
    # messageId should be logged
    assert "<20261022.mock-message-id@brevo>" in caplog.text


@pytest.mark.asyncio
async def test_brevo_unauthorized_401_no_key_leak(monkeypatch, caplog):
    """(b) Status 401 should log ERROR without leaking API key or raising."""
    test_key = "xkeysib-supersecret-invalid-key-99999"
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: Settings(
            app_secret_key="x" * 32,
            session_secret_key="y" * 32,
            brevo_api_key=test_key,
        ),
    )

    error_payload = {
        "code": "unauthorized",
        "message": "Key not found in Brevo database",
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=401,
            json=error_payload,
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with caplog.at_level(logging.ERROR, logger="spetser.email"):
            # Must NOT raise exception
            await _send_via_brevo(
                to_email="test401@example.com",
                subject="Test",
                html_body="<p>Test</p>",
                client=client,
            )

    # ERROR was logged
    assert any(record.levelno == logging.ERROR for record in caplog.records)
    # API key is never logged
    assert test_key not in caplog.text
    # First 200 chars preview of response body logged
    assert "unauthorized" in caplog.text


@pytest.mark.asyncio
async def test_brevo_timeout_suppression(monkeypatch, caplog):
    """(c) TimeoutException should log ERROR without raising exception."""
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: Settings(
            app_secret_key="x" * 32,
            session_secret_key="y" * 32,
            brevo_api_key="xkeysib-mock-key",
            email_http_timeout_seconds=0.01,
        ),
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out to api.brevo.com")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with caplog.at_level(logging.ERROR, logger="spetser.email"):
            # Must NOT raise exception
            await _send_via_brevo(
                to_email="timeout@example.com",
                subject="Timeout Test",
                html_body="<p>Timeout</p>",
                client=client,
            )

    assert any(record.levelno == logging.ERROR for record in caplog.records)
    assert "timed out" in caplog.text.lower()


@pytest.mark.asyncio
async def test_brevo_request_headers_and_body_format(monkeypatch):
    """(d) Verify URL, headers, and body schema conform exactly to Brevo v3 spec."""
    test_key = "xkeysib-mock-test-key-54321"
    monkeypatch.setattr(
        "app.services.email_service.get_settings",
        lambda: Settings(
            app_secret_key="x" * 32,
            session_secret_key="y" * 32,
            brevo_api_key=test_key,
            brevo_sender_name="Spetser Team",
            smtp_from="sender@spetser.ai",
        ),
    )

    captured_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(status_code=201, json={"messageId": "<msg-1>"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await _send_via_brevo(
            to_email="recipient@example.com",
            subject="Verification Code",
            html_body="<b>987654</b>",
            client=client,
        )

    assert len(captured_requests) == 1
    req = captured_requests[0]

    # Verify method and URL
    assert req.method == "POST"
    assert str(req.url) == "https://api.brevo.com/v3/smtp/email"

    # Verify headers
    assert req.headers.get("api-key") == test_key
    assert req.headers.get("content-type") == "application/json"
    assert req.headers.get("accept") == "application/json"

    # Verify body payload
    body = json.loads(req.content.decode("utf-8"))
    assert body["sender"] == {"name": "Spetser Team", "email": "sender@spetser.ai"}
    assert body["to"] == [{"email": "recipient@example.com"}]
    assert body["subject"] == "Verification Code"
    assert body["htmlContent"] == "<b>987654</b>"


@pytest.mark.asyncio
async def test_provider_precedence_order(monkeypatch):
    """
    Verify provider selection order:
    1. Brevo HTTP API (when brevo_api_key is set)
    2. SMTP (when smtp_user is set and brevo_api_key is empty)
    3. Development / dummy mode (when neither is set)
    """
    # Case 1: Both Brevo and SMTP set -> Brevo MUST be chosen
    settings_case1 = Settings(
        app_secret_key="x" * 32,
        session_secret_key="y" * 32,
        brevo_api_key="xkeysib-case1",
        smtp_user="smtp-user@example.com",
        smtp_password="password",
        smtp_host="smtp.gmail.com",
    )
    monkeypatch.setattr("app.services.email_service.get_settings", lambda: settings_case1)

    with patch("app.services.email_service._send_via_brevo", new_callable=AsyncMock) as mock_brevo, \
         patch("app.services.email_service._send_via_smtp", new_callable=AsyncMock) as mock_smtp:
        await _send_email_task("test@example.com", "Subj", "<p>Body</p>")
        assert mock_brevo.called
        assert not mock_smtp.called

    # Case 2: Only SMTP set -> SMTP MUST be chosen
    settings_case2 = Settings(
        app_secret_key="x" * 32,
        session_secret_key="y" * 32,
        brevo_api_key="",
        smtp_user="smtp-user@example.com",
        smtp_password="password",
        smtp_host="smtp.gmail.com",
    )
    monkeypatch.setattr("app.services.email_service.get_settings", lambda: settings_case2)

    with patch("app.services.email_service._send_via_brevo", new_callable=AsyncMock) as mock_brevo, \
         patch("app.services.email_service._send_via_smtp", new_callable=AsyncMock) as mock_smtp:
        await _send_email_task("test@example.com", "Subj", "<p>Body</p>")
        assert not mock_brevo.called
        assert mock_smtp.called

    # Case 3: Neither set -> Development mode (neither Brevo nor SMTP called)
    settings_case3 = Settings(
        app_secret_key="x" * 32,
        session_secret_key="y" * 32,
        brevo_api_key="",
        smtp_user="",
        smtp_password="",
        smtp_host="",
    )
    monkeypatch.setattr("app.services.email_service.get_settings", lambda: settings_case3)

    with patch("app.services.email_service._send_via_brevo", new_callable=AsyncMock) as mock_brevo, \
         patch("app.services.email_service._send_via_smtp", new_callable=AsyncMock) as mock_smtp:
        await _send_email_task("test@example.com", "Subj", "<p>Body</p>")
        assert not mock_brevo.called
        assert not mock_smtp.called
