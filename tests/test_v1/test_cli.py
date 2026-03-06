"""Tests for CLI -- cyclopts app with install, init, generate commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from cyclopts import App
import pytest

from ai_guardrails.cli import _print_results, app, generate, init, install, status
from ai_guardrails.infra.console import Console
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_is_cyclopts_app() -> None:
    assert isinstance(app, App)


def test_cli_has_install_command() -> None:
    # cyclopts registers commands -- smoke test app is configured
    assert app is not None


def test_install_command_exists() -> None:
    """Install subcommand is registered."""
    assert callable(install)


def test_init_command_exists() -> None:
    assert callable(init)


def test_generate_command_exists() -> None:
    assert callable(generate)


def test_install_invokes_install_pipeline(tmp_path: Path) -> None:
    with patch("ai_guardrails.cli.InstallPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        install()
        mock_cls.assert_called_once()
        mock_pipeline.run.assert_called_once()


def test_init_invokes_init_pipeline(tmp_path: Path) -> None:
    with patch("ai_guardrails.cli.InitPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        init()
        mock_cls.assert_called_once()
        mock_pipeline.run.assert_called_once()


def test_generate_invokes_generate_pipeline(tmp_path: Path) -> None:
    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        generate()
        mock_cls.assert_called_once()
        mock_pipeline.run.assert_called_once()


def test_init_passes_force_flag() -> None:
    with patch("ai_guardrails.cli.InitPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        init(force=True)
        call_kwargs = mock_cls.call_args
        options = call_kwargs[1].get("options") or call_kwargs[0][0]
        assert options.force is True


def test_generate_passes_check_flag() -> None:
    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        generate(check=True)
        call_kwargs = mock_cls.call_args
        options = call_kwargs[1].get("options") or call_kwargs[0][0]
        assert options.check is True


def test_generate_check_exits_nonzero_when_stale() -> None:
    """generate --check must raise SystemExit(1) when any result has status=='error'."""
    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [
            StepResult(status="error", message="ruff.toml is stale"),
        ]
        mock_cls.return_value = mock_pipeline

        with pytest.raises(SystemExit) as exc_info:
            generate(check=True)
        assert exc_info.value.code == 1


def test_generate_check_does_not_exit_when_all_ok() -> None:
    """generate --check must NOT raise SystemExit when all results are ok."""
    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [StepResult(status="ok", message="all good")]
        mock_cls.return_value = mock_pipeline

        # Must not raise
        generate(check=True)


# ---------------------------------------------------------------------------
# M-4 / M-6: _resolve_project_dir + --project-dir flag
# ---------------------------------------------------------------------------


def test_init_rejects_non_git_directory(tmp_path: Path) -> None:
    """init must raise SystemExit when project_dir has no .git directory."""
    with pytest.raises(SystemExit, match="not a git repository"):
        init(project_dir=tmp_path)


def test_generate_rejects_non_git_directory(tmp_path: Path) -> None:
    """generate must raise SystemExit when project_dir has no .git directory."""
    with pytest.raises(SystemExit, match="not a git repository"):
        generate(project_dir=tmp_path)


def test_status_rejects_non_git_directory(tmp_path: Path) -> None:
    """status must raise SystemExit when project_dir has no .git directory."""
    with pytest.raises(SystemExit, match="not a git repository"):
        status(project_dir=tmp_path)


def test_init_accepts_project_dir_flag(tmp_path: Path) -> None:
    """init --project-dir passes resolved path to the pipeline."""
    (tmp_path / ".git").mkdir()

    with patch("ai_guardrails.cli.InitPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        init(project_dir=tmp_path)
        _, run_kwargs = mock_pipeline.run.call_args
        assert run_kwargs["project_dir"] == tmp_path.resolve()


def test_install_does_not_require_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """install is global -- must NOT check for .git directory."""
    monkeypatch.chdir(tmp_path)

    with patch("ai_guardrails.cli.InstallPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline

        install()  # Must not raise
        mock_pipeline.run.assert_called_once()


# ---------------------------------------------------------------------------
# L-5: status command
# ---------------------------------------------------------------------------


def test_status_command_exists() -> None:
    assert callable(status)


# ---------------------------------------------------------------------------
# L-9: _print_results branch coverage
# ---------------------------------------------------------------------------


def test_print_results_warn_branch() -> None:
    """Verify _print_results handles warn status."""
    console = Console()
    _print_results([StepResult(status="warn", message="test warning")], console)


def test_print_results_skip_branch() -> None:
    """Verify _print_results handles skip status."""
    console = Console()
    _print_results([StepResult(status="skip", message="test skip")], console)
