"""
tests/unit/test_logging_redaction.py
────────────────────────────────────
Lesson 10.5 — structured logging redaction: secrets never appear in log output.
"""
from __future__ import annotations

import logging

import structlog

from app.core.logging import redact_secrets


class TestRedactSecrets:
    def test_redacts_api_key(self):
        event = {"api_key": "sk-secret-value"}
        assert redact_secrets(None, "info", event)["api_key"] == "[REDACTED]"

    def test_redacts_token(self):
        event = {"token": "abc123"}
        assert redact_secrets(None, "info", event)["token"] == "[REDACTED]"

    def test_redacts_password(self):
        event = {"password": "hunter2"}
        assert redact_secrets(None, "info", event)["password"] == "[REDACTED]"

    def test_redacts_authorization(self):
        event = {"authorization": "Bearer xyz"}
        assert redact_secrets(None, "info", event)["authorization"] == "[REDACTED]"

    def test_redacts_webhook_secret(self):
        event = {"webhook_secret": "whsec"}
        assert redact_secrets(None, "info", event)["webhook_secret"] == "[REDACTED]"

    def test_redacts_session(self):
        event = {"session": "cookie-value"}
        assert redact_secrets(None, "info", event)["session"] == "[REDACTED]"

    def test_redacts_private_key(self):
        event = {"private_key": "-----BEGIN"}
        assert redact_secrets(None, "info", event)["private_key"] == "[REDACTED]"

    def test_case_insensitive(self):
        event = {"API_KEY": "sk-x", "Secret": "s"}
        out = redact_secrets(None, "info", event)
        assert out["API_KEY"] == "[REDACTED]"
        assert out["Secret"] == "[REDACTED]"

    def test_redacts_nested_dict(self):
        event = {"config": {"api_key": "sk-nested", "model": "gpt"}}
        out = redact_secrets(None, "info", event)
        assert out["config"]["api_key"] == "[REDACTED]"
        assert out["config"]["model"] == "gpt"

    def test_keeps_non_secret_keys(self):
        event = {"user_id": "123", "status": "ok", "message": "hello"}
        out = redact_secrets(None, "info", event)
        assert out["user_id"] == "123"
        assert out["status"] == "ok"
        assert out["message"] == "hello"

    def test_empty_value_not_replaced(self):
        event = {"api_key": ""}
        assert redact_secrets(None, "info", event)["api_key"] == ""

    def test_none_value_not_replaced(self):
        event = {"api_key": None}
        assert redact_secrets(None, "info", event)["api_key"] is None


class TestEndToEndRedaction:
    def test_bound_logger_never_emits_secret(self, capsys):
        """structlog with redact_secrets in the chain must scrub before render."""
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                redact_secrets,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=False,
        )
        logger = structlog.get_logger("test.redaction")
        logger.info("payment_setup", api_key="sk-should-not-appear", invoice="inv_1")

        captured = capsys.readouterr()
        text = captured.out + captured.err
        assert "sk-should-not-appear" not in text
        assert "[REDACTED]" in text
        assert "inv_1" in text
