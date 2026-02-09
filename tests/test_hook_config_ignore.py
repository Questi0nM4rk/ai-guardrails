"""Tests for guardrails.hooks.config_ignore -- config ignore-pattern detector."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from guardrails.hooks.config_ignore import (
    _added_lines_for,
    _is_config_file,
    _staged_files,
    main,
)

if TYPE_CHECKING:
    import pytest


class TestIsConfigFile:
    """Test config filename detection."""

    def test_pyproject_toml(self) -> None:
        assert _is_config_file("pyproject.toml") is True

    def test_setup_cfg(self) -> None:
        assert _is_config_file("setup.cfg") is True

    def test_flake8(self) -> None:
        assert _is_config_file(".flake8") is True

    def test_eslintrc_json(self) -> None:
        assert _is_config_file(".eslintrc.json") is True

    def test_eslintrc_js(self) -> None:
        assert _is_config_file(".eslintrc.js") is True

    def test_eslintrc_yml(self) -> None:
        assert _is_config_file(".eslintrc.yml") is True

    def test_tsconfig_json(self) -> None:
        assert _is_config_file("tsconfig.json") is True

    def test_tslint_json(self) -> None:
        assert _is_config_file("tslint.json") is True

    def test_random_file(self) -> None:
        assert _is_config_file("README.md") is False

    def test_python_source(self) -> None:
        assert _is_config_file("main.py") is False

    def test_nested_path(self) -> None:
        assert _is_config_file("src/pyproject.toml") is True


class TestStagedFiles:
    """Test git staged file listing."""

    @patch("guardrails.hooks.config_ignore._git")
    def test_returns_staged_files(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "pyproject.toml\nsetup.cfg\n"
        result = _staged_files()
        assert result == ["pyproject.toml", "setup.cfg"]

    @patch("guardrails.hooks.config_ignore._git")
    def test_returns_empty_on_no_output(self, mock_git: MagicMock) -> None:
        mock_git.return_value = ""
        assert _staged_files() == []

    @patch("guardrails.hooks.config_ignore._git")
    def test_strips_blank_lines(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "file1.toml\n\nfile2.toml\n"
        result = _staged_files()
        assert result == ["file1.toml", "file2.toml"]


class TestAddedLinesFor:
    """Test extraction of added lines from git diff."""

    @patch("guardrails.hooks.config_ignore._git")
    def test_returns_added_lines(self, mock_git: MagicMock) -> None:
        mock_git.return_value = (
            "+++ b/pyproject.toml\n+ignore = ['E501']\n+other = 'value'\n context line\n"
        )
        result = _added_lines_for("pyproject.toml")
        assert "+ignore = ['E501']" in result
        assert "+other = 'value'" in result

    @patch("guardrails.hooks.config_ignore._git")
    def test_excludes_diff_header(self, mock_git: MagicMock) -> None:
        mock_git.return_value = "+++ b/pyproject.toml\n+new line\n"
        result = _added_lines_for("pyproject.toml")
        assert "+++ b/pyproject.toml" not in result
        assert "+new line" in result

    @patch("guardrails.hooks.config_ignore._git")
    def test_empty_diff(self, mock_git: MagicMock) -> None:
        mock_git.return_value = ""
        assert _added_lines_for("pyproject.toml") == []


class TestMain:
    """Test the main() entry point."""

    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_returns_0_when_no_staged_files(self, mock_staged: MagicMock) -> None:
        mock_staged.return_value = []
        assert main() == 0

    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_returns_0_when_no_config_files_staged(self, mock_staged: MagicMock) -> None:
        mock_staged.return_value = ["main.py", "README.md"]
        assert main() == 0

    @patch("guardrails.hooks.config_ignore._added_lines_for")
    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_returns_1_when_ignore_pattern_added(
        self, mock_staged: MagicMock, mock_added: MagicMock, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("[tool.ruff]\nignore = ['E501']\n")
        mock_staged.return_value = [str(config_file)]
        mock_added.return_value = ["+ignore = ['E501']"]
        assert main() == 1

    @patch("guardrails.hooks.config_ignore._added_lines_for")
    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_returns_0_when_no_ignore_patterns(
        self, mock_staged: MagicMock, mock_added: MagicMock, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("[tool.ruff]\nline-length = 100\n")
        mock_staged.return_value = [str(config_file)]
        mock_added.return_value = ["+line-length = 100"]
        assert main() == 0

    @patch("guardrails.hooks.config_ignore._added_lines_for")
    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_skips_autogenerated_files(
        self, mock_staged: MagicMock, mock_added: MagicMock, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("# AUTO-GENERATED by ai-guardrails\nignore = ['E501']\n")
        mock_staged.return_value = [str(config_file)]
        mock_added.return_value = ["+ignore = ['E501']"]
        assert main() == 0

    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_skips_nonexistent_file(self, mock_staged: MagicMock, tmp_path: Path) -> None:
        mock_staged.return_value = [str(tmp_path / "missing_pyproject.toml")]
        assert main() == 0

    @patch("guardrails.hooks.config_ignore._added_lines_for")
    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_detects_noqa_pattern(
        self, mock_staged: MagicMock, mock_added: MagicMock, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "setup.cfg"
        config_file.write_text("[flake8]\nper-file-ignores = src/*:E501\n")
        mock_staged.return_value = [str(config_file)]
        mock_added.return_value = ["+per-file-ignores = src/*:E501"]
        assert main() == 1

    @patch("guardrails.hooks.config_ignore._added_lines_for")
    @patch("guardrails.hooks.config_ignore._staged_files")
    def test_output_contains_error_message(
        self,
        mock_staged: MagicMock,
        mock_added: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("[tool.ruff]\nignore = ['E501']\n")
        mock_staged.return_value = [str(config_file)]
        mock_added.return_value = ["+ignore = ['E501']"]
        main()
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "Ignore pattern" in captured.out
