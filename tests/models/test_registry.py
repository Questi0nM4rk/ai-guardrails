"""Tests for ExceptionRegistry model."""

from __future__ import annotations

from typing import Any

import pytest

from ai_guardrails.models.registry import (
    ExceptionRegistry,
    FileException,
    InlineSuppression,
    RuleException,
)


def _minimal_toml() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "global_rules": {},
        "exceptions": [],
        "file_exceptions": [],
        "custom": {},
        "inline_suppressions": [],
    }


def test_from_toml_minimal_valid_data() -> None:
    reg = ExceptionRegistry.from_toml(_minimal_toml())
    assert reg.schema_version == 1
    assert reg.exceptions == []
    assert reg.file_exceptions == []


def test_from_toml_parses_global_rules() -> None:
    data = _minimal_toml()
    data["global_rules"] = {"ruff": {"ignore": ["E501"]}}
    reg = ExceptionRegistry.from_toml(data)
    assert reg.global_rules["ruff"]["ignore"] == ["E501"]


def test_from_toml_parses_rule_exceptions() -> None:
    data = _minimal_toml()
    data["exceptions"] = [
        {
            "tool": "ruff",
            "rule": "T201",
            "reason": "CLI uses print",
            "scope": "src/cli.py",
        }
    ]
    reg = ExceptionRegistry.from_toml(data)
    assert len(reg.exceptions) == 1
    exc = reg.exceptions[0]
    assert exc.tool == "ruff"
    assert exc.rule == "T201"
    assert exc.reason == "CLI uses print"
    assert exc.scope == "src/cli.py"


def test_from_toml_parses_file_exceptions() -> None:
    data = _minimal_toml()
    data["file_exceptions"] = [
        {
            "glob": "tests/**/*.py",
            "tool": "ruff",
            "rules": ["S101"],
            "reason": "Asserts OK in tests",
        }
    ]
    reg = ExceptionRegistry.from_toml(data)
    assert len(reg.file_exceptions) == 1
    fe = reg.file_exceptions[0]
    assert fe.glob == "tests/**/*.py"
    assert fe.rules == ["S101"]


def test_from_toml_missing_schema_version_raises_value_error() -> None:
    """Missing schema_version raises ValueError with helpful message."""
    data = _minimal_toml()
    del data["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        ExceptionRegistry.from_toml(data)


def test_get_ignores_returns_rules_for_tool() -> None:
    data = _minimal_toml()
    data["global_rules"] = {"ruff": {"ignore": ["E501", "W503"]}}
    reg = ExceptionRegistry.from_toml(data)
    assert reg.get_ignores("ruff") == ["E501", "W503"]


def test_get_ignores_returns_empty_for_unknown_tool() -> None:
    data = _minimal_toml()
    data["global_rules"] = {}
    reg = ExceptionRegistry.from_toml(data)
    assert reg.get_ignores("nonexistent") == []


def test_get_per_file_ignores_returns_mapping_for_tool() -> None:
    data = _minimal_toml()
    data["file_exceptions"] = [
        {
            "glob": "tests/**/*.py",
            "tool": "ruff",
            "rules": ["S101", "PLR2004"],
            "reason": "Tests are special",
        },
        {
            "glob": "scripts/**",
            "tool": "ruff",
            "rules": ["T201"],
            "reason": "Scripts print",
        },
    ]
    reg = ExceptionRegistry.from_toml(data)
    pfi = reg.get_per_file_ignores("ruff")
    assert pfi["tests/**/*.py"] == ["S101", "PLR2004"]
    assert pfi["scripts/**"] == ["T201"]


def test_get_per_file_ignores_excludes_other_tools() -> None:
    data = _minimal_toml()
    data["file_exceptions"] = [
        {
            "glob": "tests/**",
            "tool": "mypy",
            "rules": ["misc"],
            "reason": "mypy exception",
        },
    ]
    reg = ExceptionRegistry.from_toml(data)
    assert reg.get_per_file_ignores("ruff") == {}


def test_rule_exception_optional_fields_default_to_none() -> None:
    exc = RuleException(tool="ruff", rule="T201", reason="OK")
    assert exc.scope is None
    assert exc.expires is None


def test_file_exception_fields() -> None:
    fe = FileException(glob="**/*.py", tool="ruff", rules=["S101"], reason="tests")
    assert fe.glob == "**/*.py"
    assert fe.tool == "ruff"
    assert fe.rules == ["S101"]


def test_inline_suppression_fields() -> None:
    sup = InlineSuppression(
        pattern="# noqa: E501", reason="Line too long in generated code"
    )
    assert sup.pattern == "# noqa: E501"
    assert sup.reason == "Line too long in generated code"


def test_from_toml_exception_missing_tool_raises_value_error() -> None:
    """Exception entry missing 'tool' raises ValueError with field name and index."""
    data = _minimal_toml()
    data["exceptions"] = [{"rule": "T201", "reason": "OK"}]  # missing "tool"
    with pytest.raises(ValueError, match=r"Exception #1.*tool"):
        ExceptionRegistry.from_toml(data)


def test_from_toml_file_exception_missing_glob_raises_value_error() -> None:
    """File exception missing 'glob' raises ValueError with field name and index."""
    data = _minimal_toml()
    data["file_exceptions"] = [
        {"tool": "ruff", "rules": ["S101"], "reason": "test"},  # missing "glob"
    ]
    with pytest.raises(ValueError, match=r"File exception #1.*glob"):
        ExceptionRegistry.from_toml(data)


def test_from_toml_inline_suppression_missing_pattern_raises_value_error() -> None:
    """Inline suppression missing 'pattern' raises ValueError with index."""
    data = _minimal_toml()
    data["inline_suppressions"] = [{"reason": "OK"}]  # missing "pattern"
    with pytest.raises(ValueError, match=r"Inline suppression #1.*pattern"):
        ExceptionRegistry.from_toml(data)
