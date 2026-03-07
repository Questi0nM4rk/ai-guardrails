"""Tests for CheckPipeline — integration test with all steps mocked."""

from __future__ import annotations

import json
from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.check_pipeline import CheckOptions, CheckPipeline
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

_REPO_ROOT = Path(__file__).parents[3]
_DATA_DIR = _REPO_ROOT / "src" / "ai_guardrails" / "_data"


def _make_pipeline(*, baseline: Path | None = None) -> CheckPipeline:
    return CheckPipeline(
        options=CheckOptions(baseline_file=baseline),
        data_dir=_DATA_DIR,
    )


def test_check_options_defaults() -> None:
    opts = CheckOptions()
    assert opts.baseline_file is None


def test_check_pipeline_can_be_constructed() -> None:
    pipeline = _make_pipeline()
    assert pipeline is not None


def test_check_pipeline_run_returns_list(tmp_path: Path) -> None:
    """Smoke test: pipeline returns a list of StepResults on empty dir."""
    runner = FakeCommandRunner()
    # ruff returns no issues (empty JSON array)
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=0,
        stdout="[]",
    )

    pipeline = _make_pipeline()
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )

    assert isinstance(results, list)
    assert len(results) >= 1


def test_check_pipeline_no_issues_succeeds(tmp_path: Path) -> None:
    """Pipeline succeeds when ruff finds no issues and no baseline exists."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=0,
        stdout="[]",
    )

    pipeline = _make_pipeline()
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )

    assert not any(r.status == "error" for r in results)


def test_check_pipeline_with_explicit_baseline(tmp_path: Path) -> None:
    """Pipeline accepts an explicit baseline_file path."""
    baseline_path = tmp_path / "custom-baseline.json"
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=0,
        stdout="[]",
    )

    pipeline = _make_pipeline(baseline=baseline_path)
    results = pipeline.run(
        project_dir=tmp_path,
        file_manager=FakeFileManager(),
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )

    assert isinstance(results, list)


def test_check_pipeline_writes_audit_log(tmp_path: Path) -> None:
    """After a successful check run the audit JSONL is written."""
    runner = FakeCommandRunner()
    runner.register(
        ["uv", "run", "ruff", "check", "--output-format=json", str(tmp_path)],
        returncode=0,
        stdout="[]",
    )

    fm = FakeFileManager()
    pipeline = _make_pipeline()
    pipeline.run(
        project_dir=tmp_path,
        file_manager=fm,
        command_runner=runner,
        config_loader=ConfigLoader(),
        console=FakeConsole(),
    )

    audit_path = tmp_path / ".guardrails-audit.jsonl"
    # FakeFileManager.written records (path, text) tuples from append_text calls
    written_paths = [p for p, _ in fm.written]
    assert audit_path in written_paths
    content = next(text for p, text in fm.written if p == audit_path)
    record = json.loads(content.strip())
    assert record["command"] == "check"
    assert record["status"] in ("ok", "error")
    assert "timestamp" in record
    assert "new_issues" in record
