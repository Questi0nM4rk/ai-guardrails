"""Tests for guardrails.status — project health check."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from guardrails.status import (
    _EXPECTED_HOOKS,
    Check,
    CheckResult,
    StatusReport,
    check_agent_instructions,
    check_ci_workflow,
    check_configs,
    check_git_repo,
    check_hooks,
    check_precommit,
    check_registry,
    check_review_bots,
    run_status,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\n")
    return tmp_path


# --- Individual check tests ---


class TestCheckGitRepo:
    def test_ok_when_git_dir_exists(self, project_dir: Path) -> None:
        result = check_git_repo(project_dir)
        assert result.status == "ok"

    def test_fail_when_no_git(self, tmp_path: Path) -> None:
        result = check_git_repo(tmp_path)
        assert result.status == "error"
        assert "not a git repository" in result.message.lower()


class TestCheckPrecommit:
    def test_ok_when_installed(self, project_dir: Path) -> None:
        with patch("shutil.which", return_value="/usr/bin/pre-commit"):
            result = check_precommit(project_dir)
        assert result.status == "ok"

    def test_warn_when_not_installed(self, project_dir: Path) -> None:
        with patch("shutil.which", return_value=None):
            result = check_precommit(project_dir)
        assert result.status == "warn"

    def test_warn_when_hooks_not_installed(self, project_dir: Path) -> None:
        (project_dir / ".git" / "hooks" / "pre-commit").unlink()
        with patch("shutil.which", return_value="/usr/bin/pre-commit"):
            result = check_precommit(project_dir)
        assert result.status == "warn"
        assert "not installed" in result.message.lower()


class TestCheckHooks:
    def test_ok_when_all_deployed(self, project_dir: Path) -> None:
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        hooks_dir.mkdir(parents=True)
        for name in _EXPECTED_HOOKS:
            (hooks_dir / name).write_text("#!/bin/sh\n")
        result = check_hooks(project_dir)
        assert result.status == "ok"
        assert "8/8" in result.message

    def test_warn_when_missing(self, project_dir: Path) -> None:
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "format-and-stage.sh").write_text("#!/bin/sh\n")
        result = check_hooks(project_dir)
        assert result.status == "warn"

    def test_error_when_no_dir(self, project_dir: Path) -> None:
        result = check_hooks(project_dir)
        assert result.status == "error"


class TestCheckConfigs:
    def test_ok_when_editorconfig_exists(self, project_dir: Path) -> None:
        (project_dir / ".editorconfig").write_text("root = true\n")
        result = check_configs(project_dir, languages=[])
        assert result.status == "ok"

    def test_warn_when_missing(self, project_dir: Path) -> None:
        result = check_configs(project_dir, languages=[])
        assert result.status == "warn"

    def test_includes_language_configs(self, project_dir: Path) -> None:
        (project_dir / ".editorconfig").write_text("root = true\n")
        result = check_configs(project_dir, languages=["python"])
        # ruff.toml missing
        assert result.status == "warn"
        assert "ruff.toml" in result.message


class TestCheckRegistry:
    def test_ok_when_valid(self, project_dir: Path) -> None:
        (project_dir / ".guardrails-exceptions.toml").write_text("schema_version = 1\n")
        result = check_registry(project_dir)
        assert result.status == "ok"

    def test_error_when_invalid_toml(self, project_dir: Path) -> None:
        (project_dir / ".guardrails-exceptions.toml").write_text("this is not [ valid toml")
        result = check_registry(project_dir)
        assert result.status == "error"
        assert "invalid" in result.message.lower() or "toml" in result.message.lower()

    def test_skip_when_missing(self, project_dir: Path) -> None:
        result = check_registry(project_dir)
        assert result.status == "skip"


class TestCheckAgentInstructions:
    def test_ok_when_marker_present(self, project_dir: Path) -> None:
        (project_dir / "CLAUDE.md").write_text("## AI Guardrails - Code Standards\n")
        result = check_agent_instructions(project_dir)
        assert result.status == "ok"

    def test_warn_when_missing(self, project_dir: Path) -> None:
        result = check_agent_instructions(project_dir)
        assert result.status == "warn"


class TestCheckReviewBots:
    def test_ok_when_all_present(self, project_dir: Path) -> None:
        (project_dir / ".coderabbit.yaml").write_text("reviews:\n")
        (project_dir / ".deepsource.toml").write_text("version = 1\n")
        (project_dir / ".gemini").mkdir()
        (project_dir / ".gemini" / "config.yaml").write_text("platform: github\n")
        result = check_review_bots(project_dir)
        assert result.status == "ok"

    def test_warn_when_partial(self, project_dir: Path) -> None:
        (project_dir / ".coderabbit.yaml").write_text("reviews:\n")
        result = check_review_bots(project_dir)
        assert result.status == "warn"

    def test_skip_when_no_bots(self, project_dir: Path) -> None:
        result = check_review_bots(project_dir)
        assert result.status == "skip"
        assert "no review bot" in result.message.lower()


class TestCheckCiWorkflow:
    def test_ok_when_present(self, project_dir: Path) -> None:
        wf = project_dir / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "check.yml").write_text("name: Check\n")
        result = check_ci_workflow(project_dir)
        assert result.status == "ok"

    def test_skip_when_not_github(self, project_dir: Path) -> None:
        result = check_ci_workflow(project_dir)
        assert result.status == "skip"


# --- StatusReport tests ---


class TestStatusReport:
    def test_overall_ok(self) -> None:
        report = StatusReport(
            project_dir="/var/test",
            languages=["python"],
            checks=[
                CheckResult(check=Check.GIT_REPO, status="ok", message="Git repo"),
            ],
        )
        assert report.overall == "ok"

    def test_overall_degraded(self) -> None:
        report = StatusReport(
            project_dir="/var/test",
            languages=[],
            checks=[
                CheckResult(check=Check.GIT_REPO, status="ok", message="OK"),
                CheckResult(check=Check.HOOKS, status="warn", message="Missing"),
            ],
        )
        assert report.overall == "degraded"

    def test_overall_error(self) -> None:
        report = StatusReport(
            project_dir="/var/test",
            languages=[],
            checks=[
                CheckResult(check=Check.GIT_REPO, status="error", message="Not a repo"),
            ],
        )
        assert report.overall == "error"

    def test_to_json(self) -> None:
        report = StatusReport(
            project_dir="/var/test",
            languages=["python"],
            checks=[
                CheckResult(check=Check.GIT_REPO, status="ok", message="Git repo"),
            ],
        )
        data = json.loads(report.to_json())
        assert data["overall"] == "ok"
        assert data["languages"] == ["python"]
        assert len(data["checks"]) == 1

    def test_skipped_checks_dont_affect_overall(self) -> None:
        report = StatusReport(
            project_dir="/var/test",
            languages=[],
            checks=[
                CheckResult(check=Check.GIT_REPO, status="ok", message="OK"),
                CheckResult(check=Check.REGISTRY, status="skip", message="No registry"),
            ],
        )
        assert report.overall == "ok"


# --- CLI integration ---


class TestRunStatus:
    def test_returns_zero_on_healthy(self, project_dir: Path) -> None:
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        hooks_dir.mkdir(parents=True)
        for name in _EXPECTED_HOOKS:
            (hooks_dir / name).write_text("#!/bin/sh\n")
        (project_dir / ".editorconfig").write_text("root = true\n")
        (project_dir / "CLAUDE.md").write_text("## AI Guardrails - Code Standards\n")
        # Review bot configs needed for healthy status
        (project_dir / ".coderabbit.yaml").write_text("reviews:\n")
        (project_dir / ".deepsource.toml").write_text("version = 1\n")
        (project_dir / ".gemini").mkdir()
        (project_dir / ".gemini" / "config.yaml").write_text("platform: github\n")

        with patch("shutil.which", return_value="/usr/bin/pre-commit"):
            rc = run_status(project_dir=project_dir)
        assert rc == 0

    def test_returns_one_on_degraded(self, project_dir: Path) -> None:
        # Deploy hooks so no "error" status — only "warn" from missing pre-commit
        hooks_dir = project_dir / ".ai-guardrails" / "hooks"
        hooks_dir.mkdir(parents=True)
        for name in _EXPECTED_HOOKS:
            (hooks_dir / name).write_text("#!/bin/sh\n")
        with patch("shutil.which", return_value=None):
            rc = run_status(project_dir=project_dir)
        assert rc == 1

    def test_json_output(self, project_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("shutil.which", return_value="/usr/bin/pre-commit"):
            run_status(project_dir=project_dir, output_json=True)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "overall" in data
        assert "checks" in data
