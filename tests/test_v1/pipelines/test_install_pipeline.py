"""Tests for InstallPipeline — checks prerequisites, installs global config."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.install_pipeline import InstallOptions, InstallPipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager


def _make_pipeline(global_config_dir: Path | None = None) -> InstallPipeline:
    return InstallPipeline(
        options=InstallOptions(),
        global_config_dir=global_config_dir or Path("/home/test/.ai-guardrails"),
    )


def test_install_options_defaults() -> None:
    opts = InstallOptions()
    assert opts.upgrade is False


def test_install_pipeline_can_be_constructed() -> None:
    pipeline = _make_pipeline()
    assert pipeline is not None


def test_install_pipeline_checks_git(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=0, stdout="git version 2.40.0")

    pipeline = _make_pipeline(global_config_dir=tmp_path / "config")
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    assert isinstance(results, list)
    called_cmds = [tuple(c) for c in runner.calls]
    assert ("git", "--version") in called_cmds


def test_install_pipeline_checks_lefthook(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=0, stdout="git version 2.40.0")
    runner.register(["lefthook", "--version"], returncode=0, stdout="lefthook 1.11.0")

    pipeline = _make_pipeline(global_config_dir=tmp_path / "config")
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    called_cmds = [tuple(c) for c in runner.calls]
    assert ("lefthook", "--version") in called_cmds


def test_install_pipeline_creates_global_config(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=0, stdout="git version 2.40.0")
    runner.register(["lefthook", "--version"], returncode=0, stdout="lefthook 1.11.0")

    config_dir = tmp_path / "config"
    pipeline = _make_pipeline(global_config_dir=config_dir)
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    # Global config should be written
    written_paths = {p for p, _ in fm.written}
    assert any("config.toml" in str(p) for p in written_paths)


def test_install_pipeline_errors_on_missing_required_tool(tmp_path: Path) -> None:
    fm = FakeFileManager()
    runner = FakeCommandRunner()
    runner.register(["git", "--version"], returncode=1, stderr="not found")

    pipeline = _make_pipeline(global_config_dir=tmp_path / "config")
    results = pipeline.run(
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )
    # Required tools missing: pipeline stops with error status
    assert any(r.status == "error" for r in results)
    assert any("git" in r.message for r in results)
