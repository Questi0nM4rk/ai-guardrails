"""Tests for CheckStep — hold-the-line lint enforcement via baseline."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import ClassVar

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.models.baseline import BaselineEntry, BaselineStatus
from ai_guardrails.models.lint_issue import LintIssue
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.check_step import CheckStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = datetime.date(2026, 3, 7)

_RUFF_JSON_NO_ISSUES = "[]"

_RUFF_ISSUE_FINGERPRINT = "abc123def456abc1"

_RUFF_JSON_ONE_ISSUE = json.dumps(
    [
        {
            "filename": "src/foo.py",
            "location": {"row": 10, "column": 1},
            "message": "Use `X | Y` for union type annotations",
            "code": "UP007",
        }
    ]
)


def _make_fingerprint(rule: str, file: str, line_content: str = "") -> str:
    return LintIssue.compute_fingerprint(
        rule=rule,
        file=file,
        line_content=line_content,
        context_before=[],
        context_after=[],
    )


def _baseline_entry(
    fingerprint: str,
    *,
    status: BaselineStatus = BaselineStatus.LEGACY,
) -> BaselineEntry:
    return BaselineEntry(
        rule="UP007",
        fingerprint=fingerprint,
        file="src/foo.py",
        status=status,
        captured_at=_TODAY,
    )


class _FakePythonPlugin:
    """Minimal stub that satisfies the LanguagePlugin protocol for Python."""

    key = "python"
    name = "Python"
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = []

    def detect(self, project_dir: Path) -> bool:
        return True

    def generate(self, registry: object, project_dir: Path) -> dict[Path, str]:
        return {}

    def hook_config(self) -> dict[str, object]:
        return {}

    def check(self, registry: object, project_dir: Path) -> list[str]:
        return []


def _make_context(
    tmp_path: Path,
    runner: FakeCommandRunner,
    *,
    python_detected: bool = True,
) -> PipelineContext:
    languages: list[object] = [_FakePythonPlugin()] if python_detected else []
    return PipelineContext(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=languages,  # type: ignore[arg-type]
        registry=None,
        dry_run=False,
        force=False,
    )


def _write_baseline(tmp_path: Path, entries: list[BaselineEntry]) -> Path:
    baseline_path = tmp_path / ".guardrails-baseline.json"
    baseline_path.write_text(json.dumps([e.to_dict() for e in entries]))
    return baseline_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_check_step_name() -> None:
    step = CheckStep(baseline_file=Path(".guardrails-baseline.json"))
    assert step.name == "check"


def test_check_step_no_issues_returns_ok(tmp_path: Path) -> None:
    """When ruff reports no issues, step returns ok."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=0,
        stdout=_RUFF_JSON_NO_ISSUES,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok"
    assert "new" not in result.message.lower() or "0" in result.message


def test_check_step_new_issue_returns_error(tmp_path: Path) -> None:
    """When ruff reports an issue not in the baseline, step returns error."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=1,
        stdout=_RUFF_JSON_ONE_ISSUE,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    # No baseline file — all issues are new
    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "error"
    assert "UP007" in result.message or "new" in result.message.lower()


def test_check_step_baseline_suppresses_known_issue(tmp_path: Path) -> None:
    """When ruff reports an issue whose fingerprint is in the baseline as
    'legacy', the step must return ok (not a new issue)."""
    # Compute the fingerprint that CheckStep will produce for this issue
    fp = _make_fingerprint("UP007", "src/foo.py")
    entry = _baseline_entry(fp, status=BaselineStatus.LEGACY)
    baseline_path = _write_baseline(tmp_path, [entry])

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=1,
        stdout=_RUFF_JSON_ONE_ISSUE,
    )

    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok", f"Expected ok but got error: {result.message}"


def test_check_step_missing_baseline_treats_all_as_new(tmp_path: Path) -> None:
    """When no baseline file exists, every issue is treated as new."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=1,
        stdout=_RUFF_JSON_ONE_ISSUE,
    )

    # Baseline file deliberately absent
    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "error"


def test_check_step_promoted_baseline_entry_does_not_suppress(tmp_path: Path) -> None:
    """An entry with status='promoted' must NOT suppress the issue."""
    fp = _make_fingerprint("UP007", "src/foo.py")
    entry = _baseline_entry(fp, status=BaselineStatus.PROMOTED)
    baseline_path = _write_baseline(tmp_path, [entry])

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=1,
        stdout=_RUFF_JSON_ONE_ISSUE,
    )

    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "error", (
        "Promoted baseline entries should NOT suppress issues"
    )


def test_check_step_burn_down_entry_suppresses(tmp_path: Path) -> None:
    """An entry with status='burn_down' suppresses the issue like 'legacy'."""
    fp = _make_fingerprint("UP007", "src/foo.py")
    entry = _baseline_entry(fp, status=BaselineStatus.BURN_DOWN)
    baseline_path = _write_baseline(tmp_path, [entry])

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=1,
        stdout=_RUFF_JSON_ONE_ISSUE,
    )

    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok", "Burn-down baseline entries should suppress issues"


def test_check_step_no_python_detected_returns_skip(tmp_path: Path) -> None:
    """When no Python language plugin is active, step skips ruff."""
    runner = FakeCommandRunner()
    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = CheckStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner, python_detected=False)

    result = step.execute(ctx)

    assert result.status == "skip"
    assert not runner.calls  # ruff must not have been invoked


def test_check_step_validate_always_passes(tmp_path: Path) -> None:
    """validate() has no preconditions — baseline absence is handled in execute."""
    step = CheckStep(baseline_file=tmp_path / ".guardrails-baseline.json")
    ctx = _make_context(tmp_path, FakeCommandRunner())
    errors = step.validate(ctx)
    assert errors == []
