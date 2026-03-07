"""Tests for SnapshotStep — capture current lint issues as baseline."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import ClassVar

from ai_guardrails.steps.snapshot_step import SnapshotStep

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUFF_JSON_NO_ISSUES = "[]"

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_snapshot_step_name() -> None:
    step = SnapshotStep(baseline_file=Path(".guardrails-baseline.json"))
    assert step.name == "snapshot"


def test_snapshot_step_validate_always_passes(tmp_path: Path) -> None:
    """validate() has no preconditions."""
    step = SnapshotStep(baseline_file=tmp_path / ".guardrails-baseline.json")
    ctx = _make_context(tmp_path, FakeCommandRunner())
    errors = step.validate(ctx)
    assert errors == []


def test_snapshot_step_creates_baseline_from_ruff_issues(tmp_path: Path) -> None:
    """SnapshotStep writes found issues to baseline JSON."""
    src_file = tmp_path / "foo.py"
    src_file.write_text("x: int = 1\n")

    ruff_json = json.dumps(
        [
            {
                "filename": str(src_file),
                "location": {"row": 1, "column": 1},
                "message": "Test issue",
                "code": "UP007",
            }
        ]
    )

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok"
    assert "1" in result.message

    baseline = json.loads(baseline_path.read_text())
    assert len(baseline) == 1
    assert baseline[0]["rule"] == "UP007"
    assert baseline[0]["status"] == "legacy"


def test_snapshot_step_no_issues_writes_empty_baseline(tmp_path: Path) -> None:
    """When ruff reports no issues and no existing baseline, writes empty file."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=_RUFF_JSON_NO_ISSUES,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok"
    baseline = json.loads(baseline_path.read_text())
    assert baseline == []


def test_snapshot_step_preserves_existing_entries(tmp_path: Path) -> None:
    """SnapshotStep does not remove existing baseline entries even when gone."""
    old_entry = {
        "rule": "E501",
        "fingerprint": "old123abc456def7",
        "file": "old.py",
        "status": "legacy",
        "captured_at": "2026-01-01",
    }
    baseline_path = tmp_path / ".guardrails-baseline.json"
    baseline_path.write_text(json.dumps([old_entry]))

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=_RUFF_JSON_NO_ISSUES,
    )

    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok"
    baseline = json.loads(baseline_path.read_text())
    fingerprints = {e["fingerprint"] for e in baseline}
    assert "old123abc456def7" in fingerprints  # old entry preserved


def test_snapshot_step_does_not_duplicate_existing_fingerprints(
    tmp_path: Path,
) -> None:
    """When ruff returns an issue already in the baseline, it's not added again."""
    src_file = tmp_path / "foo.py"
    src_file.write_text("x: int = 1\n")

    ruff_json = json.dumps(
        [
            {
                "filename": str(src_file),
                "location": {"row": 1, "column": 1},
                "message": "Test",
                "code": "UP007",
            }
        ]
    )

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )

    # Run once to capture baseline
    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)
    step.execute(ctx)

    first_run_count = len(json.loads(baseline_path.read_text()))

    # Run again — same issue must not create duplicate entry
    runner2 = FakeCommandRunner()
    runner2.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )
    step2 = SnapshotStep(baseline_file=baseline_path)
    ctx2 = _make_context(tmp_path, runner2)
    step2.execute(ctx2)

    second_run_count = len(json.loads(baseline_path.read_text()))
    assert second_run_count == first_run_count


def test_snapshot_step_dry_run_does_not_write(tmp_path: Path) -> None:
    """With dry_run=True, SnapshotStep reports but does not write the file."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=_RUFF_JSON_NO_ISSUES,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path, dry_run=True)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok"
    assert "dry" in result.message.lower() or "would" in result.message.lower()
    assert not baseline_path.exists()


def test_snapshot_step_dry_run_with_issues_does_not_write(tmp_path: Path) -> None:
    """Dry run with issues found still does not write to disk."""
    src_file = tmp_path / "foo.py"
    src_file.write_text("x: int = 1\n")

    ruff_json = json.dumps(
        [
            {
                "filename": str(src_file),
                "location": {"row": 1, "column": 1},
                "message": "Test",
                "code": "UP007",
            }
        ]
    )

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path, dry_run=True)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    assert result.status == "ok"
    assert not baseline_path.exists()


def test_snapshot_step_message_counts_new_and_existing(tmp_path: Path) -> None:
    """Result message reports both new and existing entry counts."""
    old_entry = {
        "rule": "E501",
        "fingerprint": "old123abc456def7",
        "file": "old.py",
        "status": "legacy",
        "captured_at": "2026-01-01",
    }
    baseline_path = tmp_path / ".guardrails-baseline.json"
    baseline_path.write_text(json.dumps([old_entry]))

    src_file = tmp_path / "foo.py"
    src_file.write_text("x: int = 1\n")

    ruff_json = json.dumps(
        [
            {
                "filename": str(src_file),
                "location": {"row": 1, "column": 1},
                "message": "Test",
                "code": "UP007",
            }
        ]
    )

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )

    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)
    result = step.execute(ctx)

    # Should report total=2, new=1, existing=1
    assert result.status == "ok"
    assert "2" in result.message  # total
    assert "1 new" in result.message
    assert "1 existing" in result.message


def test_snapshot_step_no_python_detected_writes_empty_baseline(
    tmp_path: Path,
) -> None:
    """When no Python plugin is detected, snapshot writes empty baseline."""
    runner = FakeCommandRunner()
    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner, python_detected=False)

    result = step.execute(ctx)

    # No languages detected: collect_issues returns None → no issues → empty baseline
    assert result.status == "ok"
    assert not runner.calls  # ruff must not have been invoked


def test_snapshot_step_merges_new_and_existing(tmp_path: Path) -> None:
    """New issue is added; old entry is preserved; combined total is correct."""
    old_entry = {
        "rule": "E501",
        "fingerprint": "old123abc456def7",
        "file": "old.py",
        "status": "legacy",
        "captured_at": "2026-01-01",
    }
    baseline_path = tmp_path / ".guardrails-baseline.json"
    baseline_path.write_text(json.dumps([old_entry]))

    src_file = tmp_path / "foo.py"
    src_file.write_text("x: int = 1\n")

    ruff_json = json.dumps(
        [
            {
                "filename": str(src_file),
                "location": {"row": 1, "column": 1},
                "message": "Test",
                "code": "UP007",
            }
        ]
    )

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )

    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)
    step.execute(ctx)

    baseline = json.loads(baseline_path.read_text())
    assert len(baseline) == 2
    fingerprints = {e["fingerprint"] for e in baseline}
    assert "old123abc456def7" in fingerprints
    rules = {e["rule"] for e in baseline}
    assert "UP007" in rules
    assert "E501" in rules


def test_snapshot_step_captured_at_is_today(tmp_path: Path) -> None:
    """New entries are tagged with today's date."""
    src_file = tmp_path / "foo.py"
    src_file.write_text("x: int = 1\n")

    ruff_json = json.dumps(
        [
            {
                "filename": str(src_file),
                "location": {"row": 1, "column": 1},
                "message": "Test",
                "code": "UP007",
            }
        ]
    )

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=ruff_json,
    )

    baseline_path = tmp_path / ".guardrails-baseline.json"
    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)
    step.execute(ctx)

    baseline = json.loads(baseline_path.read_text())
    assert len(baseline) == 1
    today = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    assert baseline[0]["captured_at"] == today


def test_snapshot_step_corrupted_baseline_handled_gracefully(
    tmp_path: Path,
) -> None:
    """Corrupted baseline file is treated as if empty — no crash."""
    baseline_path = tmp_path / ".guardrails-baseline.json"
    baseline_path.write_text("NOT VALID JSON {{{{")

    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        stdout=_RUFF_JSON_NO_ISSUES,
    )

    step = SnapshotStep(baseline_file=baseline_path)
    ctx = _make_context(tmp_path, runner)

    result = step.execute(ctx)

    # Should not raise; corrupted baseline starts fresh
    assert result.status == "ok"
