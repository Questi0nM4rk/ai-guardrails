"""Tests for ReportStep."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.report_step import ReportStep
from tests.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

if TYPE_CHECKING:
    from pathlib import Path


def _make_ctx(tmp_path: Path, *, lines: list[str] | None = None) -> PipelineContext:
    if lines is not None:
        audit = tmp_path / ".guardrails-audit.jsonl"
        audit.write_text("\n".join(lines) + "\n")
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


def test_report_step_no_audit_file(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    result = ReportStep().execute(ctx)
    assert result.status == "ok"
    assert "No audit log" in result.message


def test_report_step_shows_recent_runs(tmp_path: Path) -> None:
    records = [
        json.dumps(
            {
                "timestamp": "2026-03-07T12:00:00+00:00",
                "status": "ok",
                "new_issues": 0,
            }
        ),
        json.dumps(
            {
                "timestamp": "2026-03-06T11:00:00+00:00",
                "status": "error",
                "new_issues": 2,
            }
        ),
    ]
    ctx = _make_ctx(tmp_path, lines=records)
    result = ReportStep().execute(ctx)
    assert result.status == "ok"
    console: FakeConsole = ctx.console  # type: ignore[assignment]
    assert any("2026-03-07" in txt for _, txt in console.messages)
    assert any("error" in txt for _, txt in console.messages)


def test_report_step_validate_returns_empty(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    assert ReportStep().validate(ctx) == []


def test_report_step_skips_malformed_json_lines(tmp_path: Path) -> None:
    records = [
        json.dumps(
            {"timestamp": "2026-03-07T10:00:00+00:00", "status": "ok", "new_issues": 0}
        ),
        "not-valid-json",
        json.dumps(
            {"timestamp": "2026-03-07T11:00:00+00:00", "status": "ok", "new_issues": 1}
        ),
    ]
    ctx = _make_ctx(tmp_path, lines=records)
    result = ReportStep().execute(ctx)
    assert result.status == "ok"
    assert "2" in result.message  # 2 valid records shown


def test_report_step_limits_to_last_10_rows(tmp_path: Path) -> None:
    records = [
        json.dumps(
            {
                "timestamp": f"2026-03-0{i % 9 + 1}T10:00:00+00:00",
                "status": "ok",
                "new_issues": 0,
                "command": "check",
            }
        )
        for i in range(15)
    ]
    ctx = _make_ctx(tmp_path, lines=records)
    result = ReportStep().execute(ctx)
    assert result.status == "ok"
    assert "10" in result.message
