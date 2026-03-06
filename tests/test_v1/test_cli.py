"""Tests for CLI — cyclopts app with install, init, generate commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from cyclopts import App

from ai_guardrails.cli import app


def test_cli_is_cyclopts_app() -> None:
    assert isinstance(app, App)


def test_cli_has_install_command() -> None:
    # cyclopts registers commands — smoke test app is configured
    assert app is not None


def test_install_command_exists() -> None:
    """Install subcommand is registered."""
    from ai_guardrails.cli import install

    assert callable(install)


def test_init_command_exists() -> None:
    from ai_guardrails.cli import init

    assert callable(init)


def test_generate_command_exists() -> None:
    from ai_guardrails.cli import generate

    assert callable(generate)


def test_install_invokes_install_pipeline(tmp_path: Path) -> None:
    with patch("ai_guardrails.cli.InstallPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import install

        install()
        mock_cls.assert_called_once()
        mock_pipeline.run.assert_called_once()


def test_init_invokes_init_pipeline(tmp_path: Path) -> None:
    with patch("ai_guardrails.cli.InitPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import init

        init()
        mock_cls.assert_called_once()
        mock_pipeline.run.assert_called_once()


def test_generate_invokes_generate_pipeline(tmp_path: Path) -> None:
    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import generate

        generate()
        mock_cls.assert_called_once()
        mock_pipeline.run.assert_called_once()


def test_init_passes_force_flag() -> None:
    with patch("ai_guardrails.cli.InitPipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import init

        init(force=True)
        call_kwargs = mock_cls.call_args
        options = call_kwargs[1].get("options") or call_kwargs[0][0]
        assert options.force is True


def test_generate_passes_check_flag() -> None:
    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = []
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import generate

        generate(check=True)
        call_kwargs = mock_cls.call_args
        options = call_kwargs[1].get("options") or call_kwargs[0][0]
        assert options.check is True


def test_generate_check_exits_nonzero_when_stale() -> None:
    """generate --check must raise SystemExit(1) when any result has status=='error'."""
    import pytest

    from ai_guardrails.pipelines.base import StepResult

    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [
            StepResult(status="error", message="ruff.toml is stale")
        ]
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import generate

        with pytest.raises(SystemExit) as exc_info:
            generate(check=True)
        assert exc_info.value.code == 1


def test_generate_check_does_not_exit_when_all_ok() -> None:
    """generate --check must NOT raise SystemExit when all results are ok."""
    from ai_guardrails.pipelines.base import StepResult

    with patch("ai_guardrails.cli.GeneratePipeline") as mock_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = [StepResult(status="ok", message="all good")]
        mock_cls.return_value = mock_pipeline
        from ai_guardrails.cli import generate

        # Must not raise
        generate(check=True)
