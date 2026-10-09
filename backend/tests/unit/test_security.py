"""
tests/unit/test_security.py
────────────────────────────
Unit tests for Phase 2 security utilities:
- bcrypt password hashing/verification
- JWT access/refresh token creation and decoding
- Fernet encrypt/decrypt roundtrip
- API key masking
- Webhook signature verification
- Secret redaction in logging
- Config production fail-fast
"""
from __future__ import annotations

import hashlib
import hmac
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.errors import AuthenticationError, SessionExpiredError
from app.core.logging import redact_secrets
from app.core.security import (
    compute_signature,
    create_access_token,
    create_refresh_token,
    decrypt_secret,
    decode_token,
    encrypt_secret,
    hash_password,
    is_access_token,
    mask_api_key,
    verify_password,
    verify_signature,
)

# Test-only Fernet key (NOT a production secret — safe in tests).
TEST_FERNET_KEY = "LLeCKZHDwXkZKHWNMRWIk9amTreqLfrXoldMsyvzRXo="


@pytest.fixture(autouse=True)
def _enable_fernet(monkeypatch):
    """Ensure a Fernet key exists for encryption tests."""
    monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", TEST_FERNET_KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ──────────────────────────────────────────────────────────────────────────────
# Password hashing
# ──────────────────────────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_password_returns_bcrypt_hash(self):
        hashed = hash_password("password123")
        assert hashed.startswith("$2")
        # Salt makes each hash unique
        assert hash_password("password123") != hashed

    def test_verify_password_correct(self):
        hashed = hash_password("password123")
        assert verify_password("password123", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("password123")
        assert verify_password("wrongpass", hashed) is False

    def test_verify_password_malformed_hash(self):
        assert verify_password("password123", "not-a-hash") is False
        assert verify_password("", "not-a-hash") is False
        assert verify_password("password123", "") is False

    def test_hash_password_rejects_empty(self):
        with pytest.raises(ValueError):
            hash_password("")

    def test_hash_password_rejects_too_long(self):
        with pytest.raises(ValueError):
            hash_password("x" * 200)

    def test_long_password_still_verifiable_under_limit(self):
        password = "x" * 71
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        # Over the limit must not verify
        assert verify_password(password + "y", hashed) is False


# ──────────────────────────────────────────────────────────────────────────────
# JWT tokens
# ──────────────────────────────────────────────────────────────────────────────


class TestTokens:
    def test_access_token_roundtrip(self):
        subject = str(uuid.uuid4())
        token = create_access_token(subject, role="student", is_premium=True)
        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["role"] == "student"
        assert payload["premium"] is True
        assert payload["type"] == "access"
        assert is_access_token(token)

    def test_refresh_token_roundtrip(self):
        subject = str(uuid.uuid4())
        token = create_refresh_token(subject)
        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"
        assert is_access_token(token) is False

    def test_refresh_exp_is_after_access_exp(self):
        access = jwt.decode(create_access_token("s1"), get_settings().app_secret_key,
                            algorithms=["HS256"])
        refresh = jwt.decode(create_refresh_token("s1"), get_settings().app_secret_key,
                             algorithms=["HS256"])
        assert refresh["exp"] > access["exp"]

    def test_decode_rejects_tampered_token(self):
        token = create_access_token(str(uuid.uuid4()))
        tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
        with pytest.raises(AuthenticationError):
            decode_token(tampered)

    def test_decode_rejects_garbage(self):
        with pytest.raises(AuthenticationError):
            decode_token("not.a.jwt")

    def test_decode_rejects_expired_token(self):
        token = create_access_token("s", expires_delta_seconds=-10)
        with pytest.raises(SessionExpiredError):
            decode_token(token)

    def test_token_signed_with_app_secret(self):
        settings = get_settings()
        token = create_access_token("subject-1")
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        assert payload["sub"] == "subject-1"
        # A different key must fail
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-key-wrong-key-wrong-key", algorithms=["HS256"])


# ──────────────────────────────────────────────────────────────────────────────
# Fernet encryption
# ──────────────────────────────────────────────────────────────────────────────


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "sk-ant-api03-AbC123secretkey"
        encrypted = encrypt_secret(plaintext)
        assert encrypted != plaintext
        assert decrypt_secret(encrypted) == plaintext

    def test_ciphertext_is_base64_like(self):
        encrypted = encrypt_secret("hello")
        assert encrypted.startswith("gAAAAA")

    def test_two_encryptions_of_same_plaintext_differ(self):
        a = encrypt_secret("same")
        b = encrypt_secret("same")
        assert a != b  # random IV per encryption
        assert decrypt_secret(a) == decrypt_secret(b) == "same"

    def test_decrypt_garbage_raises(self):
        from cryptography.fernet import InvalidToken

        with pytest.raises(InvalidToken):
            decrypt_secret("gAAAAA-not-valid")


# ──────────────────────────────────────────────────────────────────────────────
# API key masking
# ──────────────────────────────────────────────────────────────────────────────


class TestMasking:
    def test_mask_long_key(self):
        key = "sk-ant-1234567890abcdef"
        assert mask_api_key(key) == "sk-***cdef"
        assert "1234567890" not in mask_api_key(key)

    def test_mask_short_key_is_fully_hidden(self):
        assert mask_api_key("short") == "***"
        assert mask_api_key("") == "***"

    def test_mask_never_returns_full_key(self):
        key = "sk-live-abcdef123456"
        masked = mask_api_key(key)
        assert key not in masked


# ──────────────────────────────────────────────────────────────────────────────
# Webhook signatures
# ──────────────────────────────────────────────────────────────────────────────


class TestWebhookSignature:
    PAYLOAD = b'{"payment_id": "123", "status": "confirmed"}'
    SECRET = "webhook-shared-secret"

    def test_valid_signature_accepted(self):
        sig = compute_signature(self.PAYLOAD, self.SECRET)
        assert verify_signature(self.PAYLOAD, sig, self.SECRET) is True

    def test_invalid_signature_rejected(self):
        assert verify_signature(self.PAYLOAD, "wrong", self.SECRET) is False

    def test_wrong_secret_rejected(self):
        sig = compute_signature(self.PAYLOAD, "other-secret")
        assert verify_signature(self.PAYLOAD, sig, self.SECRET) is False

    def test_tampered_payload_rejected(self):
        sig = compute_signature(self.PAYLOAD, self.SECRET)
        tampered = b'{"payment_id": "999", "status": "confirmed"}'
        assert verify_signature(tampered, sig, self.SECRET) is False

    def test_empty_signature_rejected(self):
        assert verify_signature(self.PAYLOAD, "", self.SECRET) is False

    def test_hmac_is_sha512(self):
        expected = hmac.new(
            self.SECRET.encode(), self.PAYLOAD, hashlib.sha512
        ).hexdigest()
        assert compute_signature(self.PAYLOAD, self.SECRET) == expected


# ──────────────────────────────────────────────────────────────────────────────
# Log secret redaction
# ──────────────────────────────────────────────────────────────────────────────


class TestLogRedaction:
    def test_api_key_key_redacted(self):
        event = redact_secrets(None, "info", {"anthropic_api_key": "sk-ant-secret"})
        assert event["anthropic_api_key"] == "[REDACTED]"

    def test_token_and_password_redacted(self):
        event = redact_secrets(
            None, "info", {"access_token": "abc", "password": "p4ss"}
        )
        assert event["access_token"] == "[REDACTED]"
        assert event["password"] == "[REDACTED]"

    def test_non_secret_keys_untouched(self):
        event = redact_secrets(None, "info", {"user_id": "123", "count": 5})
        assert event["user_id"] == "123"
        assert event["count"] == 5

    def test_nested_secret_redacted(self):
        event = redact_secrets(
            None, "info", {"provider": {"api_key": "sk-secret", "name": "anthropic"}}
        )
        assert event["provider"]["api_key"] == "[REDACTED]"
        assert event["provider"]["name"] == "anthropic"

    def test_empty_secret_value_untouched(self):
        event = redact_secrets(None, "info", {"api_key": ""})
        assert event["api_key"] == ""


# ──────────────────────────────────────────────────────────────────────────────
# Config validation / fail-fast
# ──────────────────────────────────────────────────────────────────────────────


class TestConfigValidation:
    def _base_env(self) -> dict[str, str]:
        return {
            "APP_ENV": "production",
            "APP_SECRET_KEY": "x" * 32,
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "SESSION_SECRET_KEY": "y" * 32,
        }

    def _set_env(self, monkeypatch, env: dict[str, str]) -> None:
        for k, v in env.items():
            monkeypatch.setenv(k, v)

    def test_production_requires_llm_key(self, monkeypatch):
        get_settings.cache_clear()
        self._set_env(monkeypatch, self._base_env())
        monkeypatch.delenv("LLM_MASTER_ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("CRYPTO_PAYMENT_API_KEY", raising=False)
        with pytest.raises(ValueError, match="LLM_MASTER_ENCRYPTION_KEY"):
            get_settings()

    def test_production_requires_payment_key(self, monkeypatch):
        get_settings.cache_clear()
        self._set_env(monkeypatch, self._base_env())
        monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", TEST_FERNET_KEY)
        monkeypatch.delenv("CRYPTO_PAYMENT_API_KEY", raising=False)
        with pytest.raises(ValueError, match="CRYPTO_PAYMENT_API_KEY"):
            get_settings()

    def test_production_requires_webhook_secret(self, monkeypatch):
        get_settings.cache_clear()
        self._set_env(monkeypatch, self._base_env())
        monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", TEST_FERNET_KEY)
        monkeypatch.setenv("CRYPTO_PAYMENT_API_KEY", "pay-key")
        monkeypatch.delenv("CRYPTO_PAYMENT_WEBHOOK_SECRET", raising=False)
        with pytest.raises(ValueError, match="CRYPTO_PAYMENT_WEBHOOK_SECRET"):
            get_settings()

    def test_production_with_all_secrets_loads(self, monkeypatch):
        get_settings.cache_clear()
        self._set_env(monkeypatch, self._base_env())
        monkeypatch.setenv("LLM_MASTER_ENCRYPTION_KEY", TEST_FERNET_KEY)
        monkeypatch.setenv("CRYPTO_PAYMENT_API_KEY", "pay-key")
        monkeypatch.setenv("CRYPTO_PAYMENT_WEBHOOK_SECRET", "wh-secret")
        settings = get_settings()
        assert settings.is_production is True

    def test_development_missing_secrets_still_loads(self, monkeypatch):
        """Fail-fast only applies in production; dev must start without secrets."""
        get_settings.cache_clear()
        env = self._base_env()
        env["APP_ENV"] = "development"
        self._set_env(monkeypatch, env)
        monkeypatch.delenv("LLM_MASTER_ENCRYPTION_KEY", raising=False)
        settings = get_settings()
        assert settings.is_development is True
        assert settings.llm_master_encryption_key == ""
