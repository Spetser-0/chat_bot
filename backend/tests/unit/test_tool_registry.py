"""
tests/unit/test_tool_registry.py
─────────────────────────────────
Unit tests for the safe tool registry (Lesson 4.4).
"""
from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.services.tool_registry import (
    get_tool,
    list_tools,
    validate_tool_binding,
)


class TestGetTool:
    def test_known_tool(self):
        assert get_tool("calculator").enabled

    def test_unknown_tool_raises(self):
        with pytest.raises(ValidationError):
            get_tool("delete_database")

    def test_list_tools_hides_disabled_by_default(self):
        names = [t.name for t in list_tools()]
        assert names == ["web_search", "calculator"]

    def test_list_tools_can_include_reserved(self):
        names = [t.name for t in list_tools(include_disabled=True)]
        assert "code_executor" in names and "file_reader" in names


class TestValidateBinding:
    def test_valid_web_search_config(self):
        validate_tool_binding("web_search", {"max_results": 5,
                                             "region": "ar", "safe_search": True})

    def test_none_config_ok(self):
        validate_tool_binding("calculator", None)

    def test_reserved_tool_cannot_bind(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("code_executor", None)

    def test_unknown_key_rejected(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("calculator", {"eval_mode": "unsafe"})

    def test_wrong_type_rejected(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("calculator", {"precision": "high"})

    def test_bool_is_not_int(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("web_search", {"max_results": True})

    def test_too_many_keys_rejected(self):
        big = {f"k{i}": i for i in range(11)}
        with pytest.raises(ValidationError):
            validate_tool_binding("calculator", big)

    def test_long_string_rejected(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("web_search", {"region": "x" * 501})

    def test_non_dict_config_rejected(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("calculator", ["precision", 2])

    def test_unknown_tool_rejected_via_binding(self):
        with pytest.raises(ValidationError):
            validate_tool_binding("shell", None)
