"""Tests for guardrails.cli -- unified CLI entry point."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from guardrails import __version__
from guardrails.cli import _get_version, main


class TestVersion:
    """Test version retrieval."""

    def test_returns_version_string(self) -> None:
        version = _get_version()
        assert version == __version__

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit, match="0"):
            main(["--version"])
        captured = capsys.readouterr()
        assert __version__ in captured.out


class TestSubcommandRequired:
    """Test that a subcommand is required."""

    def test_no_subcommand_exits_2(self) -> None:
        with pytest.raises(SystemExit, match="2"):
            main([])


class TestInitSubcommand:
    """Test init subcommand dispatches to run_init."""

    @patch("guardrails.cli._cmd_init")
    def test_dispatches_to_init(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        result = main(["init"])
        mock_cmd.assert_called_once()
        assert result == 0

    @patch("guardrails.cli._cmd_init")
    def test_init_with_type_flag(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["init", "--type", "python"])
        args = mock_cmd.call_args[0][0]
        assert args.project_type == "python"

    @patch("guardrails.cli._cmd_init")
    def test_init_with_force_flag(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["init", "--force"])
        args = mock_cmd.call_args[0][0]
        assert args.force is True

    @patch("guardrails.cli._cmd_init")
    def test_init_with_ci_flag(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["init", "--ci"])
        args = mock_cmd.call_args[0][0]
        assert args.ci is True

    @patch("guardrails.cli._cmd_init")
    def test_init_with_no_precommit(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["init", "--no-precommit"])
        args = mock_cmd.call_args[0][0]
        assert args.no_precommit is True


class TestGenerateSubcommand:
    """Test generate subcommand dispatches to run_generate_configs."""

    @patch("guardrails.cli._cmd_generate")
    def test_dispatches_to_generate(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        result = main(["generate"])
        mock_cmd.assert_called_once()
        assert result == 0

    @patch("guardrails.cli._cmd_generate")
    def test_generate_with_dry_run(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["generate", "--dry-run"])
        args = mock_cmd.call_args[0][0]
        assert args.dry_run is True
        assert args.check is False

    @patch("guardrails.cli._cmd_generate")
    def test_generate_with_check(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["generate", "--check"])
        args = mock_cmd.call_args[0][0]
        assert args.check is True
        assert args.dry_run is False

    @patch("guardrails.cli._cmd_generate")
    def test_generate_with_project_dir(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["generate", "/some/path"])
        args = mock_cmd.call_args[0][0]
        assert args.project_dir == "/some/path"

    def test_generate_dry_run_and_check_mutually_exclusive(self) -> None:
        with pytest.raises(SystemExit, match="2"):
            main(["generate", "--dry-run", "--check"])


class TestReviewSubcommand:
    """Test review subcommand dispatches to run_review."""

    @patch("guardrails.cli._cmd_review")
    def test_dispatches_to_review(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        result = main(["review"])
        mock_cmd.assert_called_once()
        assert result == 0

    @patch("guardrails.cli._cmd_review")
    def test_review_with_pr_number(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["review", "--pr", "42"])
        args = mock_cmd.call_args[0][0]
        assert args.pr == 42

    @patch("guardrails.cli._cmd_review")
    def test_review_with_pretty(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["review", "--pretty"])
        args = mock_cmd.call_args[0][0]
        assert args.pretty is True

    @patch("guardrails.cli._cmd_review")
    def test_review_with_severity(self, mock_cmd: MagicMock) -> None:
        mock_cmd.return_value = 0
        main(["review", "--severity", "major"])
        args = mock_cmd.call_args[0][0]
        assert args.severity == "major"
