"""
tests/unit/test_input_validation.py
────────────────────────────────────
Lesson 10.3 — control-char stripping + chat schema edge cases.
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.validation import sanitize_user_text, strip_control_chars
from app.schemas.chat import MAX_MESSAGE_CHARS, ChatCompletionRequest


class TestStripControlChars:
    def test_removes_null_and_bel(self):
        assert strip_control_chars("hello\x00world\x07") == "helloworld"

    def test_keeps_newlines_and_tabs(self):
        assert strip_control_chars("a\nb\tc") == "a\nb\tc"

    def test_keeps_arabic_and_emoji(self):
        s = "مرحبا 👋🏻"
        assert strip_control_chars(s) == s

    def test_removes_c1_controls(self):
        assert strip_control_chars("a\x80b\x9Fc") == "abc"

    def test_empty_stays_empty(self):
        assert strip_control_chars("") == ""


class TestSanitizeUserText:
    def test_strips_edges(self):
        assert sanitize_user_text("  hi  ") == "hi"

    def test_caps_length(self):
        assert sanitize_user_text("abcdef", max_length=3) == "abc"

    def test_control_then_strip(self):
        assert sanitize_user_text("\x00  secret\x07  ") == "secret"


class TestChatCompletionRequest:
    def test_valid_minimal(self):
        r = ChatCompletionRequest(message="مرحبا")
        assert r.message == "مرحبا"
        assert r.stream is True
        assert r.regenerate is False

    def test_empty_after_strip_rejected(self):
        with pytest.raises(PydanticValidationError):
            ChatCompletionRequest(message="   ")

    def test_null_bytes_stripped(self):
        r = ChatCompletionRequest(message="مرح\x00با")
        assert "\x00" not in r.message
        assert r.message == "مرحبا"

    def test_over_max_length_rejected(self):
        with pytest.raises(PydanticValidationError):
            ChatCompletionRequest(message="x" * (MAX_MESSAGE_CHARS + 1))

    def test_exactly_max_length_ok(self):
        r = ChatCompletionRequest(message="x" * MAX_MESSAGE_CHARS)
        assert len(r.message) == MAX_MESSAGE_CHARS

    def test_invalid_skill_slug_rejected(self):
        with pytest.raises(PydanticValidationError):
            ChatCompletionRequest(message="hi", skill_slug="Bad Slug!")

    def test_valid_skill_slug(self):
        r = ChatCompletionRequest(message="hi", skill_slug="math-helper_1")
        assert r.skill_slug == "math-helper_1"

    def test_regenerate_without_conversation_rejected(self):
        with pytest.raises(PydanticValidationError):
            ChatCompletionRequest(message="hi", regenerate=True)

    def test_regenerate_with_conversation_ok(self):
        r = ChatCompletionRequest(
            message="hi",
            conversation_id=uuid.uuid4(),
            regenerate=True,
        )
        assert r.regenerate is True

    def test_conversation_id_must_be_uuid(self):
        with pytest.raises(PydanticValidationError):
            ChatCompletionRequest(message="hi", conversation_id="not-a-uuid")
