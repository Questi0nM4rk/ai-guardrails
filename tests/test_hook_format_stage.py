"""Tests for guardrails.hooks.format_stage -- format-and-restage hook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from guardrails.hooks.format_stage import (
    _FORMATTERS,
    _file_hash,
    _git_staged_files,
    _run_formatter,
    main,
)


class TestFormattersDict:
    """Test the _FORMATTERS dictionary coverage."""

    def test_python_formatters(self) -> None:
        assert ".py" in _FORMATTERS
        cmds = _FORMATTERS[".py"]
        assert len(cmds) == 2
        assert cmds[0][0] == "ruff"
        assert cmds[1][0] == "ruff"

    def test_shell_formatters(self) -> None:
        assert ".sh" in _FORMATTERS
        assert ".bash" in _FORMATTERS
        assert _FORMATTERS[".sh"][0][0] == "shfmt"

    def test_markdown_formatter(self) -> None:
        assert ".md" in _FORMATTERS
        assert _FORMATTERS[".md"][0][0] == "markdownlint-cli2"

    def test_typescript_formatters(self) -> None:
        for ext in (".ts", ".tsx", ".js", ".jsx", ".json"):
            assert ext in _FORMATTERS, f"Missing formatter for {ext}"
            assert _FORMATTERS[ext][0][0] == "biome"

    def test_toml_formatter(self) -> None:
        assert ".toml" in _FORMATTERS
        assert _FORMATTERS[".toml"][0][0] == "taplo"


class TestGitStagedFiles:
    """Test git staged file listing."""

    @patch("guardrails.hooks.format_stage.subprocess.run")
    def test_returns_staged_files(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "file1.py\nfile2.ts\n"
        result = _git_staged_files()
        assert result == ["file1.py", "file2.ts"]

    @patch("guardrails.hooks.format_stage.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        assert _git_staged_files() == []

    @patch("guardrails.hooks.format_stage.subprocess.run")
    def test_strips_blank_lines(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "file1.py\n\nfile2.py\n"
        result = _git_staged_files()
        assert result == ["file1.py", "file2.py"]


class TestRunFormatter:
    """Test individual formatter execution."""

    @patch("guardrails.hooks.format_stage.subprocess.run")
    def test_runs_command_with_filepath(self, mock_run: MagicMock) -> None:
        _run_formatter(["ruff", "format"], "test.py")
        mock_run.assert_called_once_with(
            ["ruff", "format", "test.py"],
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("guardrails.hooks.format_stage.subprocess.run", side_effect=FileNotFoundError)
    def test_silently_skips_missing_formatter(self, _mock_run: MagicMock) -> None:
        """Missing formatter should not raise."""
        _run_formatter(["nonexistent-tool", "--fix"], "test.py")


class TestFileHash:
    """Test file hash computation."""

    def test_returns_hex_digest(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("content\n")
        h = _file_hash(str(f))
        assert h is not None
        assert len(h) == 64  # SHA-256 hex digest

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("same\n")
        f2.write_text("same\n")
        assert _file_hash(str(f1)) == _file_hash(str(f2))

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("content1\n")
        f2.write_text("content2\n")
        assert _file_hash(str(f1)) != _file_hash(str(f2))

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert _file_hash(str(tmp_path / "missing.py")) is None


class TestMain:
    """Test the main() entry point."""

    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_returns_0_when_no_staged_files(self, mock_staged: MagicMock) -> None:
        mock_staged.return_value = []
        assert main() == 0

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._run_formatter")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_formats_python_files(
        self,
        mock_staged: MagicMock,
        mock_format: MagicMock,
        _mock_add: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        mock_staged.return_value = [str(f)]
        assert main() == 0
        assert mock_format.call_count == 2

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._run_formatter")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_skips_unknown_extensions(
        self,
        mock_staged: MagicMock,
        mock_format: MagicMock,
        _mock_add: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b,c\n")
        mock_staged.return_value = [str(f)]
        assert main() == 0
        mock_format.assert_not_called()

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_restages_modified_files(
        self, mock_staged: MagicMock, mock_add: MagicMock, tmp_path: Path
    ) -> None:
        """Files modified by formatter should be re-staged."""
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        mock_staged.return_value = [str(f)]

        def change_file(_cmd: list[str], filepath: str) -> None:
            Path(filepath).write_text("x = 1  # formatted\n")

        with patch("guardrails.hooks.format_stage._run_formatter", side_effect=change_file):
            assert main() == 0

        mock_add.assert_called_once_with(str(f))

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._run_formatter")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_does_not_restage_unchanged_files(
        self,
        mock_staged: MagicMock,
        _mock_format: MagicMock,
        mock_add: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Files not modified by formatter should not be re-staged."""
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        mock_staged.return_value = [str(f)]
        assert main() == 0
        mock_add.assert_not_called()

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._run_formatter")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_skips_nonexistent_staged_files(
        self,
        mock_staged: MagicMock,
        mock_format: MagicMock,
        _mock_add: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_staged.return_value = [str(tmp_path / "deleted.py")]
        assert main() == 0
        mock_format.assert_not_called()

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._run_formatter")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_formats_toml_files(
        self,
        mock_staged: MagicMock,
        mock_format: MagicMock,
        _mock_add: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "config.toml"
        f.write_text('[project]\nname = "test"\n')
        mock_staged.return_value = [str(f)]
        assert main() == 0
        mock_format.assert_called_once()
        assert mock_format.call_args[0][0][0] == "taplo"

    @patch("guardrails.hooks.format_stage._git_add")
    @patch("guardrails.hooks.format_stage._run_formatter")
    @patch("guardrails.hooks.format_stage._git_staged_files")
    def test_formats_shell_files(
        self,
        mock_staged: MagicMock,
        mock_format: MagicMock,
        _mock_add: MagicMock,
        tmp_path: Path,
    ) -> None:
        f = tmp_path / "script.sh"
        f.write_text("#!/bin/bash\necho hello\n")
        mock_staged.return_value = [str(f)]
        assert main() == 0
        mock_format.assert_called_once()
        assert mock_format.call_args[0][0][0] == "shfmt"
