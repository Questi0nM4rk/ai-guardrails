"""Tests for pipeline framework — PipelineContext, StepResult, PipelineStep protocol."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.pipelines.base import (
    Pipeline,
    PipelineContext,
    StepResult,
)
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager


def _make_context(tmp_path: Path) -> PipelineContext:
    from ai_guardrails.infra.config_loader import ConfigLoader

    return PipelineContext(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=[],
        registry=None,
        dry_run=False,
        force=False,
    )


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------


def test_step_result_ok() -> None:
    r = StepResult(status="ok", message="done")
    assert r.status == "ok"
    assert r.message == "done"


def test_step_result_skip() -> None:
    r = StepResult(status="skip", message="already exists")
    assert r.status == "skip"


def test_step_result_error() -> None:
    r = StepResult(status="error", message="failed")
    assert r.status == "error"


def test_step_result_warn() -> None:
    r = StepResult(status="warn", message="not ideal")
    assert r.status == "warn"


# ---------------------------------------------------------------------------
# Pipeline context
# ---------------------------------------------------------------------------


def test_pipeline_context_has_expected_fields(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    assert ctx.project_dir == tmp_path
    assert ctx.languages == []
    assert ctx.registry is None
    assert ctx.dry_run is False
    assert ctx.force is False


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


class _OkStep:
    name = "ok-step"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(status="ok", message="ok-step done")


class _SkipStep:
    name = "skip-step"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(status="skip", message="already exists")


class _WarnStep:
    name = "warn-step"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(status="warn", message="something is off")


class _ErrorStep:
    name = "error-step"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(status="error", message="fatal error")


class _ValidateFailStep:
    name = "validate-fail-step"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return ["missing required file"]

    def execute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(status="ok", message="executed")


class _AfterErrorStep:
    """Step that should NOT run after an error step."""

    name = "after-error-step"
    executed = False

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        _AfterErrorStep.executed = True
        return StepResult(status="ok", message="ran after error")


def test_pipeline_runs_all_ok_steps(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    pipeline = Pipeline(steps=[_OkStep(), _SkipStep()])
    results = pipeline.run(ctx)
    assert len(results) == 2
    assert results[0].status == "ok"
    assert results[1].status == "skip"


def test_pipeline_stops_on_error(tmp_path: Path) -> None:
    _AfterErrorStep.executed = False
    ctx = _make_context(tmp_path)
    after = _AfterErrorStep()
    pipeline = Pipeline(steps=[_ErrorStep(), after])
    results = pipeline.run(ctx)
    assert len(results) == 1
    assert results[0].status == "error"
    assert not _AfterErrorStep.executed


def test_pipeline_continues_on_warn(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    pipeline = Pipeline(steps=[_WarnStep(), _OkStep()])
    results = pipeline.run(ctx)
    assert len(results) == 2
    assert results[0].status == "warn"
    assert results[1].status == "ok"


def test_pipeline_validate_errors_stop_step(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    pipeline = Pipeline(steps=[_ValidateFailStep()])
    results = pipeline.run(ctx)
    assert len(results) == 1
    assert results[0].status == "error"
    assert "missing required file" in results[0].message


def test_pipeline_success_returns_true_for_all_ok(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    pipeline = Pipeline(steps=[_OkStep(), _SkipStep()])
    results = pipeline.run(ctx)
    assert pipeline.succeeded(results) is True


def test_pipeline_success_returns_false_on_error(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    pipeline = Pipeline(steps=[_ErrorStep()])
    results = pipeline.run(ctx)
    assert pipeline.succeeded(results) is False


def test_pipeline_success_returns_true_with_warns(tmp_path: Path) -> None:
    ctx = _make_context(tmp_path)
    pipeline = Pipeline(steps=[_WarnStep()])
    results = pipeline.run(ctx)
    assert pipeline.succeeded(results) is True
