"""Tests for SetupCIStep — copies CI workflow template."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.setup_ci import SetupCIStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_CI_TEMPLATE = (
    Path(__file__).parents[3]
    / "src"
    / "ai_guardrails"
    / "_data"
    / "templates"
    / "workflows"
    / "check.yml"
)
_CI_OUTPUT = Path(".github/workflows/check.yml")


def _make_context(
    tmp_path: Path, *, force: bool = False
) -> tuple[PipelineContext, FakeFileManager]:
    fm = FakeFileManager()
    ctx = PipelineContext(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=[],
        registry=None,
        dry_run=False,
        force=force,
    )
    return ctx, fm


def test_setup_ci_step_name() -> None:
    step = SetupCIStep(template_path=_CI_TEMPLATE)
    assert step.name == "setup-ci"


def test_setup_ci_validate_fails_if_template_missing(tmp_path: Path) -> None:
    step = SetupCIStep(template_path=tmp_path / "missing.yml")
    ctx, _ = _make_context(tmp_path)
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert "template" in errors[0].lower()


def test_setup_ci_validate_passes(tmp_path: Path) -> None:
    step = SetupCIStep(template_path=_CI_TEMPLATE)
    ctx, _ = _make_context(tmp_path)
    assert step.validate(ctx) == []


def test_setup_ci_creates_workflow_file(tmp_path: Path) -> None:
    step = SetupCIStep(template_path=_CI_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    written_paths = {p for p, _ in fm.written}
    assert (tmp_path / _CI_OUTPUT) in written_paths


def test_setup_ci_skips_if_exists_without_force(tmp_path: Path) -> None:
    step = SetupCIStep(template_path=_CI_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    fm.seed(tmp_path / _CI_OUTPUT, "# existing\n")
    result = step.execute(ctx)
    assert result.status == "skip"
    assert not fm.written


def test_setup_ci_overwrites_with_force(tmp_path: Path) -> None:
    step = SetupCIStep(template_path=_CI_TEMPLATE)
    ctx, fm = _make_context(tmp_path, force=True)
    fm.seed(tmp_path / _CI_OUTPUT, "# old\n")
    result = step.execute(ctx)
    assert result.status == "ok"
    assert any(p == tmp_path / _CI_OUTPUT for p, _ in fm.written)


def test_setup_ci_content_comes_from_template(tmp_path: Path) -> None:
    step = SetupCIStep(template_path=_CI_TEMPLATE)
    ctx, fm = _make_context(tmp_path)
    step.execute(ctx)
    written = dict(fm.written)
    content = written.get(tmp_path / _CI_OUTPUT, "")
    assert (
        "lefthook" in content
        or "ai-guardrails" in content
        or "check" in content.lower()
    )


def test_check_yml_template_contains_action_reference() -> None:
    """The CI workflow template includes the ai-guardrails action step."""
    template = _CI_TEMPLATE.read_text()
    assert "Questi0nM4rk/ai-guardrails" in template


def test_action_yml_is_valid_yaml() -> None:
    """action.yml exists, is valid YAML, and has the expected structure."""
    action = Path(__file__).parents[3] / "action.yml"
    assert action.exists(), "action.yml must exist at the repo root"
    data = yaml.safe_load(action.read_text())
    assert data["name"] == "AI Guardrails Check"
    assert data["runs"]["using"] == "composite"


def test_action_yml_defines_expected_inputs() -> None:
    """action.yml exposes the required inputs for CI integration.

    Inputs: mode, baseline, upload-sarif, python-version.
    """
    action = Path(__file__).parents[3] / "action.yml"
    data = yaml.safe_load(action.read_text())
    inputs = data.get("inputs", {})
    for expected in ("mode", "baseline", "upload-sarif", "python-version"):
        assert expected in inputs, f"Missing input: {expected}"


def test_action_yml_defines_new_issues_output() -> None:
    """action.yml exposes a new-issues output."""
    action = Path(__file__).parents[3] / "action.yml"
    data = yaml.safe_load(action.read_text())
    outputs = data.get("outputs", {})
    assert "new-issues" in outputs, "Missing output: new-issues"
