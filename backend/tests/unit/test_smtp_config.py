"""
SMTP Configuration Validation Tests
─────────────────────────────────────
Ensures the app fails fast in production without SMTP config.
"""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_development_allows_empty_smtp():
    """Development mode should work without SMTP config."""
    settings = Settings(
        app_env="development",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        # SMTP fields intentionally empty
    )
    assert settings.smtp_user == ""
    assert settings.smtp_password == ""


def test_production_requires_smtp_user():
    """Production must have SMTP_USER configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            smtp_user="",  # ← Empty in production
            smtp_password="some-password",
            smtp_host="smtp.gmail.com",
        )

    errors = exc_info.value.errors()
    assert any("smtp_user" in str(e["loc"]) for e in errors)
    assert any("required in production" in e["msg"] for e in errors)


def test_production_requires_smtp_password():
    """Production must have SMTP_PASSWORD configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            smtp_user="user@example.com",
            smtp_password="",  # ← Empty in production
            smtp_host="smtp.gmail.com",
        )

    errors = exc_info.value.errors()
    assert any("smtp_password" in str(e["loc"]) for e in errors)


def test_production_requires_smtp_host():
    """Production must have SMTP_HOST configured."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_secret_key="test-secret-key-at-least-32-chars-long",
            session_secret_key="test-session-key-at-least-32-chars-long",
            smtp_user="user@example.com",
            smtp_password="password",
            smtp_host="",  # ← Empty in production
        )

    errors = exc_info.value.errors()
    assert any("smtp_host" in str(e["loc"]) for e in errors)


def test_production_with_valid_smtp_succeeds():
    """Production with all SMTP vars should initialize successfully."""
    settings = Settings(
        app_env="production",
        app_secret_key="test-secret-key-at-least-32-chars-long",
        session_secret_key="test-session-key-at-least-32-chars-long",
        smtp_user="user@example.com",
        smtp_password="password123",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_from="noreply@example.com",
    )
    assert settings.smtp_user == "user@example.com"
