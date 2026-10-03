"""
tests/unit/test_auth.py
─────────────────────────
Unit tests for authentication service and session token handling.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.errors import AuthenticationError
from app.services.auth import (
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "mysecretpassword"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correctpassword")
        assert not verify_password("wrongpassword", hashed)

    def test_empty_password_fails(self):
        hashed = hash_password("somepassword")
        assert not verify_password("", hashed)


class TestSessionTokens:
    def test_create_and_decode(self):
        student_id = uuid.uuid4()
        token = create_session_token(student_id, "student")
        data = decode_session_token(token)
        assert data["sub"] == str(student_id)
        assert data["role"] == "student"

    def test_tampered_token_raises(self):
        token = create_session_token(uuid.uuid4(), "student")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(AuthenticationError):
            decode_session_token(tampered)

    def test_developer_role_preserved(self):
        student_id = uuid.uuid4()
        token = create_session_token(student_id, "developer")
        data = decode_session_token(token)
        assert data["role"] == "developer"
