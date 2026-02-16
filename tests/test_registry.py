"""Tests for the exception registry parser and validator."""

from __future__ import annotations

import datetime
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest
from guardrails.registry import ExceptionRegistry


@pytest.fixture
def minimal_toml(tmp_path: Path) -> Path:
    """Minimal valid registry file."""
    p = tmp_path / ".guardrails-exceptions.toml"
    p.write_text(
        dedent("""\
        schema_version = 1
    """)
    )
    return p


@pytest.fixture
def full_toml(tmp_path: Path) -> Path:
    """Full registry with all sections."""
    p = tmp_path / ".guardrails-exceptions.toml"
    p.write_text(
        dedent("""\
        schema_version = 1

        [global.ruff]
        "W191" = "formatter-conflict"
        "D" = "docstrings not enforced"

        [global.markdownlint]
        "MD013" = "line-length handled by editors"

        [global.codespell]
        skip = [".git", "*.lock"]
        ignore_words = ["brin"]

        [global.pyright]
        reportMissingTypeStubs = false

        [[file_exceptions]]
        glob = "tests/**/*.py"
        tool = "ruff"
        rules = ["S101", "ARG001"]
        reason = "Test files need asserts and fixtures"

        [[file_exceptions]]
        glob = ["*.config.ts", "*.config.js"]
        tool = "biome"
        rules = ["style/noDefaultExport"]
        reason = "Config files use default exports"

        [[inline_suppressions]]
        pattern = "noqa: BLE001"
        glob = "**/tools/*.py"
        reason = "MCP tool boundaries"

        [[inline_suppressions]]
        pattern = "shellcheck disable=SC2317"
        glob = ["**/*.sh", "**/*.bash"]
        reason = "Indirect function calls"

        [skip]
        semgrep = ["tests/"]
        codespell = [".git"]
    """)
    )
    return p


class TestRegistryLoading:
    """Test TOML parsing and dataclass construction."""

    def test_load_minimal(self, minimal_toml: Path) -> None:
        reg = ExceptionRegistry.load(minimal_toml)
        assert reg.schema_version == 1
        assert reg.global_rules == {}
        assert reg.file_exceptions == []
        assert reg.inline_suppressions == []
        assert reg.skip == {}

    def test_load_full(self, full_toml: Path) -> None:
        reg = ExceptionRegistry.load(full_toml)
        assert reg.schema_version == 1

        # Global ruff rules
        assert "W191" in reg.global_rules["ruff"]
        assert reg.global_rules["ruff"]["D"] == "docstrings not enforced"

        # Global markdownlint
        assert "MD013" in reg.global_rules["markdownlint"]

        # Global codespell
        assert reg.global_rules["codespell"]["skip"] == [".git", "*.lock"]
        assert reg.global_rules["codespell"]["ignore_words"] == ["brin"]

        # Global pyright
        assert reg.global_rules["pyright"]["reportMissingTypeStubs"] is False

        # File exceptions
        assert len(reg.file_exceptions) == 2
        fe = reg.file_exceptions[0]
        assert fe.tool == "ruff"
        assert fe.glob == ["tests/**/*.py"]
        assert "S101" in fe.rules
        assert fe.reason == "Test files need asserts and fixtures"

        # String glob gets normalized to list
        fe_biome = reg.file_exceptions[1]
        assert fe_biome.glob == ["*.config.ts", "*.config.js"]

        # Inline suppressions
        assert len(reg.inline_suppressions) == 2
        sup = reg.inline_suppressions[0]
        assert sup.pattern == "noqa: BLE001"
        assert sup.glob == ["**/tools/*.py"]

        # String glob normalized to list
        sup2 = reg.inline_suppressions[1]
        assert sup2.glob == ["**/*.sh", "**/*.bash"]

        # Skip
        assert reg.skip["semgrep"] == ["tests/"]

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ExceptionRegistry.load(tmp_path / "nonexistent.toml")

    def test_load_invalid_toml(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.toml"
        p.write_text("this is not [ valid toml")
        with pytest.raises(ValueError, match="parse"):
            ExceptionRegistry.load(p)

    def test_load_missing_schema_version(self, tmp_path: Path) -> None:
        p = tmp_path / "no_version.toml"
        p.write_text('[global.ruff]\n"W191" = "conflict"\n')
        with pytest.raises(ValueError, match="schema_version"):
            ExceptionRegistry.load(p)


class TestRegistryValidation:
    """Test the validate() method catches bad data."""

    def test_valid_registry(self, full_toml: Path) -> None:
        reg = ExceptionRegistry.load(full_toml)
        errors = reg.validate()
        assert errors == []

    def test_file_exception_missing_reason(self, tmp_path: Path) -> None:
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[file_exceptions]]
            glob = "tests/**"
            tool = "ruff"
            rules = ["S101"]
        """)
        )
        reg = ExceptionRegistry.load(p)
        errors = reg.validate()
        assert any("reason" in e for e in errors)

    def test_inline_suppression_missing_reason(self, tmp_path: Path) -> None:
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[inline_suppressions]]
            pattern = "noqa: BLE001"
            glob = "**/*.py"
        """)
        )
        reg = ExceptionRegistry.load(p)
        errors = reg.validate()
        assert any("reason" in e for e in errors)

    def test_global_ruff_rule_without_reason(self, tmp_path: Path) -> None:
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [global.ruff]
            "W191" = ""
        """)
        )
        reg = ExceptionRegistry.load(p)
        errors = reg.validate()
        assert any("reason" in e.lower() or "empty" in e.lower() for e in errors)


class TestRegistryHelpers:
    """Test helper methods on ExceptionRegistry."""

    def test_get_ruff_ignores(self, full_toml: Path) -> None:
        reg = ExceptionRegistry.load(full_toml)
        ignores = reg.get_global_ignores("ruff")
        assert "W191" in ignores
        assert "D" in ignores

    def test_get_file_exceptions_for_tool(self, full_toml: Path) -> None:
        reg = ExceptionRegistry.load(full_toml)
        ruff_exceptions = reg.get_file_exceptions("ruff")
        assert len(ruff_exceptions) == 1
        assert ruff_exceptions[0].tool == "ruff"

        biome_exceptions = reg.get_file_exceptions("biome")
        assert len(biome_exceptions) == 1

    def test_get_file_exceptions_empty(self, full_toml: Path) -> None:
        reg = ExceptionRegistry.load(full_toml)
        assert reg.get_file_exceptions("shellcheck") == []


class TestExpiresField:
    """Test the optional ``expires`` field on exceptions."""

    def test_file_exception_parses_expires(self, tmp_path: Path) -> None:
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[file_exceptions]]
            glob = "tests/**"
            tool = "ruff"
            rules = ["S101"]
            reason = "Temporary exception"
            expires = 2026-06-01
        """)
        )
        reg = ExceptionRegistry.load(p)
        fe = reg.file_exceptions[0]
        assert fe.expires == datetime.date(2026, 6, 1)

    def test_file_exception_no_expires(self, full_toml: Path) -> None:
        """Exceptions without expires should have None."""
        reg = ExceptionRegistry.load(full_toml)
        assert reg.file_exceptions[0].expires is None

    def test_inline_suppression_parses_expires(self, tmp_path: Path) -> None:
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[inline_suppressions]]
            pattern = "noqa: BLE001"
            glob = "**/*.py"
            reason = "Temporary"
            expires = 2026-03-15
        """)
        )
        reg = ExceptionRegistry.load(p)
        sup = reg.inline_suppressions[0]
        assert sup.expires == datetime.date(2026, 3, 15)

    def test_validate_warns_expired_file_exception(self, tmp_path: Path) -> None:
        """Expired exceptions should produce a validation error."""
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[file_exceptions]]
            glob = "tests/**"
            tool = "ruff"
            rules = ["S101"]
            reason = "Was temporary"
            expires = 2025-01-01
        """)
        )
        reg = ExceptionRegistry.load(p)
        with patch("guardrails.registry._today", return_value=datetime.date(2025, 2, 1)):
            errors = reg.validate()
        assert any("expired" in e.lower() for e in errors)

    def test_validate_warns_expired_inline_suppression(self, tmp_path: Path) -> None:
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[inline_suppressions]]
            pattern = "noqa: BLE001"
            glob = "**/*.py"
            reason = "Temporary"
            expires = 2025-06-01
        """)
        )
        reg = ExceptionRegistry.load(p)
        with patch("guardrails.registry._today", return_value=datetime.date(2025, 7, 1)):
            errors = reg.validate()
        assert any("expired" in e.lower() for e in errors)

    def test_validate_ok_for_future_expires(self, tmp_path: Path) -> None:
        """Non-expired exceptions should not produce errors."""
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[file_exceptions]]
            glob = "tests/**"
            tool = "ruff"
            rules = ["S101"]
            reason = "Still valid"
            expires = 2099-12-31
        """)
        )
        reg = ExceptionRegistry.load(p)
        errors = reg.validate()
        assert not any("expired" in e.lower() for e in errors)

    def test_get_expired_returns_expired_only(self, tmp_path: Path) -> None:
        """get_expired() should return only expired exceptions."""
        p = tmp_path / "test.toml"
        p.write_text(
            dedent("""\
            schema_version = 1

            [[file_exceptions]]
            glob = "old/**"
            tool = "ruff"
            rules = ["S101"]
            reason = "Expired one"
            expires = 2025-01-01

            [[file_exceptions]]
            glob = "new/**"
            tool = "ruff"
            rules = ["S101"]
            reason = "Still valid"
            expires = 2099-12-31

            [[file_exceptions]]
            glob = "permanent/**"
            tool = "ruff"
            rules = ["S101"]
            reason = "No expiry"
        """)
        )
        reg = ExceptionRegistry.load(p)
        with patch("guardrails.registry._today", return_value=datetime.date(2025, 6, 1)):
            expired = reg.get_expired()
        assert len(expired) == 1
        assert expired[0].glob == ["old/**"]
