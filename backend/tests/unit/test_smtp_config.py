"""
Email Configuration Validation Tests
────────────────────────────────────
Ensures the app fails fast in production if neither Brevo nor SMTP is configured.
"""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_development_allows_empty_smtp():
    """Development mode should work without any email config."""
    settings = Settings(
        app_env="development",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        brevo_api_key="",
        smtp_user="",
        smtp_password="",
        smtp_host="",
    )
    assert settings.smtp_user == ""
    assert settings.smtp_password == ""
    assert settings.brevo_api_key == ""


def test_production_requires_at_least_one_email_provider():
    """Production fails if neither Brevo nor SMTP is configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            brevo_api_key="",
            smtp_user="",
            smtp_password="",
            smtp_host="",
        )

    errors = exc_info.value.errors()
    assert any("Email provider configuration is required in production" in e["msg"] for e in errors)
    assert any("BREVO_API_KEY" in e["msg"] for e in errors)
    assert any("SMTP_HOST" in e["msg"] for e in errors)


def test_production_with_brevo_only_succeeds():
    """Production succeeds when only BREVO_API_KEY is configured (Render recommended)."""
    settings = Settings(
        app_env="production",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        brevo_api_key="xkeysib-mock-api-key-test-value",
        brevo_sender_name="Spetser Team",
        smtp_user="",
        smtp_password="",
        smtp_host="",
    )
    assert settings.brevo_api_key == "xkeysib-mock-api-key-test-value"
    assert settings.brevo_sender_name == "Spetser Team"


def test_production_with_valid_smtp_succeeds():
    """Production succeeds when all 3 SMTP vars are configured."""
    settings = Settings(
        app_env="production",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        brevo_api_key="",
        smtp_user="user@example.com",
        smtp_password="password123",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_from="noreply@example.com",
    )
    assert settings.smtp_user == "user@example.com"
    assert settings.smtp_host == "smtp.gmail.com"


def test_production_requires_smtp_user():
    """Incomplete SMTP without Brevo (missing smtp_user) fails in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            brevo_api_key="",
            smtp_user="",  # Missing
            smtp_password="some-password",
            smtp_host="smtp.gmail.com",
        )

    errors = exc_info.value.errors()
    assert any("Email provider configuration is required in production" in e["msg"] for e in errors)


def test_production_requires_smtp_password():
    """Incomplete SMTP without Brevo (missing smtp_password) fails in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            brevo_api_key="",
            smtp_user="user@example.com",
            smtp_password="",  # Missing
            smtp_host="smtp.gmail.com",
        )

    errors = exc_info.value.errors()
    assert any("Email provider configuration is required in production" in e["msg"] for e in errors)


def test_production_requires_smtp_host():
    """Incomplete SMTP without Brevo (missing smtp_host) fails in production."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            brevo_api_key="",
            smtp_user="user@example.com",
            smtp_password="password",
            smtp_host="",  # Missing
        )

    errors = exc_info.value.errors()
    assert any("Email provider configuration is required in production" in e["msg"] for e in errors)
