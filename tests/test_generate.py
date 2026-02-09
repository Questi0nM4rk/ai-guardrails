"""Tests for guardrails.generate -- config generation from exception registry."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from guardrails.generate import _load_registry, run_generate_configs

if TYPE_CHECKING:
    import pytest


class TestLoadRegistry:
    """Test registry loading with error handling."""

    def test_load_valid_registry(self, tmp_path: Path) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text(
            dedent("""\
            schema_version = 1

            [global.ruff]
            "E501" = "line length handled by formatter"
        """)
        )
        result = _load_registry(tmp_path)
        assert result is not None
        assert result.schema_version == 1

    def test_load_missing_registry(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        result = _load_registry(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_load_invalid_toml(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("invalid toml [[[")
        result = _load_registry(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_load_missing_schema_version(self, tmp_path: Path) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text('[global.ruff]\n"E501" = "reason"\n')
        result = _load_registry(tmp_path)
        assert result is None

    def test_load_with_validation_errors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text(
            dedent("""\
            schema_version = 1

            [global.ruff]
            "E501" = ""
        """)
        )
        result = _load_registry(tmp_path)
        assert result is None
        captured = capsys.readouterr()
        assert "Validation" in captured.err


class TestRunGenerateConfigsDryRun:
    """Test dry-run mode (validate only)."""

    def test_dry_run_valid_registry(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")
        result = run_generate_configs(project_dir=str(tmp_path), dry_run=True)
        assert result is True
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_dry_run_missing_registry(self, tmp_path: Path) -> None:
        result = run_generate_configs(project_dir=str(tmp_path), dry_run=True)
        assert result is False


class TestRunGenerateConfigsCheck:
    """Test check mode (compare against existing)."""

    def test_check_returns_false_when_no_registry(self, tmp_path: Path) -> None:
        result = run_generate_configs(project_dir=str(tmp_path), check=True)
        assert result is False


class TestRunGenerateConfigsGenerate:
    """Test actual generation mode."""

    def test_returns_false_when_no_registry(self, tmp_path: Path) -> None:
        result = run_generate_configs(project_dir=str(tmp_path))
        assert result is False

    @patch("guardrails.generate._generate_to_dir")
    def test_generates_configs(
        self,
        mock_gen: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")

        def write_fake_config(registry: object, project_path: Path, output_dir: Path) -> list[str]:
            (output_dir / "ruff.toml").write_text("# generated\n")
            return ["ruff.toml"]

        mock_gen.side_effect = write_fake_config

        result = run_generate_configs(project_dir=str(tmp_path))
        assert result is True
        captured = capsys.readouterr()
        assert "ruff.toml" in captured.out

    @patch("guardrails.generate._generate_to_dir", side_effect=RuntimeError("boom"))
    def test_handles_generation_error(
        self,
        _mock_gen: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        registry_file = tmp_path / ".guardrails-exceptions.toml"
        registry_file.write_text("schema_version = 1\n")

        result = run_generate_configs(project_dir=str(tmp_path))
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.err
