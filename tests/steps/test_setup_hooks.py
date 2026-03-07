"""Tests for SetupHooksStep — runs lefthook install after config generation."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.pipelines.init_pipeline import InitOptions, InitPipeline
from ai_guardrails.steps.setup_hooks import SetupHooksStep
from tests.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_REPO_ROOT = Path(__file__).parents[2]
_DATA_DIR = _REPO_ROOT / "src" / "ai_guardrails" / "_data"
_REGISTRY_TEMPLATE = _DATA_DIR / "templates" / "guardrails-exceptions.toml"
_CI_TEMPLATE = _DATA_DIR / "templates" / "workflows" / "check.yml"
_AGENT_TEMPLATE = _DATA_DIR / "templates" / "CLAUDE.md.guardrails"
_CONFIGS_DIR = _DATA_DIR / "configs"


def _make_ctx(
    tmp_path: Path,
    runner: FakeCommandRunner | None = None,
) -> PipelineContext:
    return PipelineContext(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner or FakeCommandRunner(),
        config_loader=None,  # type: ignore[arg-type]
        console=FakeConsole(),
        languages=[],
        registry=None,
        dry_run=False,
        force=False,
    )


def _run_init_pipeline(
    tmp_path: Path, runner: FakeCommandRunner, *, no_hooks: bool
) -> None:
    pipeline = InitPipeline(
        options=InitOptions(no_hooks=no_hooks),
        data_dir=_DATA_DIR,
        configs_dir=_CONFIGS_DIR,
        registry_template=_REGISTRY_TEMPLATE,
        ci_template=_CI_TEMPLATE,
        agent_template=_AGENT_TEMPLATE,
    )
    pipeline.run(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )


def test_setup_hooks_step_name() -> None:
    step = SetupHooksStep()
    assert step.name == "setup-hooks"


def test_setup_hooks_runs_lefthook_install(tmp_path: Path) -> None:
    """Happy path: lefthook install succeeds, returns ok."""
    runner = FakeCommandRunner()
    ctx = _make_ctx(tmp_path, runner)

    step = SetupHooksStep()
    result = step.execute(ctx)

    assert result.status == "ok"
    assert (
        "lefthook install" in result.message.lower()
        or "hooks installed" in result.message.lower()
    )
    assert runner.calls == [["lefthook", "install"]]


def test_setup_hooks_returns_warn_on_failure(tmp_path: Path) -> None:
    """If lefthook is not installed or returns non-zero, returns warn (not error)."""
    runner = FakeCommandRunner()
    runner.register(
        ["lefthook", "install"],
        returncode=1,
        stderr="lefthook: command not found",
    )
    ctx = _make_ctx(tmp_path, runner)

    step = SetupHooksStep()
    result = step.execute(ctx)

    assert result.status == "warn"
    assert "lefthook install failed" in result.message


def test_setup_hooks_returns_warn_when_binary_missing(tmp_path: Path) -> None:
    """CommandRunner returns 'No such file' stderr when binary is missing."""
    runner = FakeCommandRunner()
    runner.register(
        ["lefthook", "install"],
        returncode=1,
        stderr="[Errno 2] No such file or directory: 'lefthook'",
    )
    ctx = _make_ctx(tmp_path, runner)

    step = SetupHooksStep()
    result = step.execute(ctx)

    assert result.status == "warn"
    assert "lefthook" in result.message.lower()


def test_setup_hooks_validate_returns_empty(tmp_path: Path) -> None:
    """validate() has no preconditions — always returns []."""
    ctx = _make_ctx(tmp_path)
    step = SetupHooksStep()
    assert step.validate(ctx) == []


def test_setup_hooks_skipped_via_no_hooks(tmp_path: Path) -> None:
    """Pipeline with no_hooks=True must not call lefthook install."""
    runner = FakeCommandRunner()
    _run_init_pipeline(tmp_path, runner, no_hooks=True)
    assert ["lefthook", "install"] not in runner.calls


def test_setup_hooks_called_by_default(tmp_path: Path) -> None:
    """Pipeline WITHOUT no_hooks flag must call lefthook install."""
    runner = FakeCommandRunner()
    _run_init_pipeline(tmp_path, runner, no_hooks=False)
    assert ["lefthook", "install"] in runner.calls


def test_setup_hooks_not_found_in_stderr_returns_lefthook_hint(
    tmp_path: Path,
) -> None:
    """When stderr contains 'not found', return warn with install hint."""
    runner = FakeCommandRunner()
    runner.register(
        ["lefthook", "install"],
        returncode=1,
        stderr="lefthook: not found",
    )
    ctx = _make_ctx(tmp_path, runner)

    step = SetupHooksStep()
    result = step.execute(ctx)

    assert result.status == "warn"
    assert (
        "lefthook not found" in result.message.lower()
        or "not found" in result.message.lower()
    )
