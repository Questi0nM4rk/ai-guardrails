"""Tests for ValidateGovernanceStep — locked rules, budgets, profile floor."""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_guardrails.models.exception_record import ExceptionRecord
from ai_guardrails.models.governance import LockRule, OrgPolicy, TeamPolicy
from ai_guardrails.models.registry import ExceptionRegistry
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.validate_governance import ValidateGovernanceStep


def _make_context(
    exceptions: list[ExceptionRecord] | None = None,
    project_dir: Path | None = None,
    tmp_path: Path | None = None,
) -> PipelineContext:
    registry = MagicMock(spec=ExceptionRegistry)
    registry.exceptions = exceptions or []
    return PipelineContext(
        project_dir=project_dir or tmp_path or Path.cwd(),
        file_manager=MagicMock(),
        command_runner=MagicMock(),
        config_loader=MagicMock(),
        console=MagicMock(),
        languages=[],
        registry=registry,
        dry_run=False,
        force=False,
        check=False,
    )


def _make_exception(rule: str, *, approved: bool = True) -> ExceptionRecord:
    return ExceptionRecord(
        id="a1b2c3d4",
        rule=rule,
        glob="src/**/*.py",
        reason="Test reason",
        proposed_by="test",
        approved_by="alice" if approved else None,
        expires=datetime.date(2027, 1, 1),
        ticket=None,
        created=datetime.date(2026, 1, 1),
    )


def _make_org(locked_rules: dict[str, LockRule] | None = None) -> OrgPolicy:
    return OrgPolicy(
        locked_rules=locked_rules or {},
        default_profile="standard",
        allowed_profiles=("standard", "strict"),
    )


def _make_team(
    locked_rules: dict[str, LockRule] | None = None,
    budget: int | None = None,
) -> TeamPolicy:
    return TeamPolicy(
        name="platform",
        owners=("alice",),
        profile="standard",
        exception_budget=budget,
        owns=(),
        locked_rules=locked_rules or {},
        overridable_rules=frozenset(),
    )


# --- no policy: always passes ---


def test_validate_governance_passes_with_no_policies(tmp_path: Path):
    ctx = _make_context(tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=None
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=None,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "ok"


# --- org locked rules ---


def test_validate_governance_fails_for_locked_org_rule(tmp_path: Path):
    lock = LockRule(rule="ruff/S603", reason="Use CommandRunner.")
    org = _make_org(locked_rules={"ruff_S603": lock})
    exc = _make_exception("ruff/S603")
    ctx = _make_context(exceptions=[exc], tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=org
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=None,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "error"
    assert "ruff/S603" in result.message
    assert "org" in result.message.lower()


def test_validate_governance_passes_for_non_locked_rule(tmp_path: Path):
    lock = LockRule(rule="ruff/S603", reason="Use CommandRunner.")
    org = _make_org(locked_rules={"ruff_S603": lock})
    exc = _make_exception("ruff/E501")  # different rule, not locked
    ctx = _make_context(exceptions=[exc], tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=org
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=None,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "ok"


# --- team locked rules ---


def test_validate_governance_fails_for_locked_team_rule(tmp_path: Path):
    lock = LockRule(rule="ruff/ARG002", reason="No unused args.")
    team = _make_team(locked_rules={"ruff_ARG002": lock})
    exc = _make_exception("ruff/ARG002")
    ctx = _make_context(exceptions=[exc], tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=None
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=team,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "error"
    assert "ruff/ARG002" in result.message
    assert "team" in result.message.lower()


# --- exception budget ---


def test_validate_governance_fails_when_over_budget(tmp_path: Path):
    team = _make_team(budget=2)
    exceptions = [_make_exception(f"ruff/E{i}", approved=True) for i in range(3)]
    ctx = _make_context(exceptions=exceptions, tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=None
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=team,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "error"
    assert "budget" in result.message.lower()


def test_validate_governance_passes_within_budget(tmp_path: Path):
    team = _make_team(budget=5)
    exceptions = [_make_exception(f"ruff/E{i}", approved=True) for i in range(3)]
    ctx = _make_context(exceptions=exceptions, tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=None
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=team,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "ok"


def test_validate_governance_budget_counts_only_approved(tmp_path: Path):
    """Pending exceptions (approved_by=None) do not count toward the budget."""
    team = _make_team(budget=1)
    exceptions = [
        _make_exception("ruff/E501", approved=True),  # counts
        _make_exception("ruff/E502", approved=False),  # pending — does NOT count
    ]
    ctx = _make_context(exceptions=exceptions, tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=None
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=team,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "ok"


def test_validate_governance_unlimited_budget(tmp_path: Path):
    """budget=None means unlimited — never fails on count."""
    team = _make_team(budget=None)
    exceptions = [_make_exception(f"ruff/E{i}", approved=True) for i in range(100)]
    ctx = _make_context(exceptions=exceptions, tmp_path=tmp_path)
    step = ValidateGovernanceStep()
    with (
        patch(
            "ai_guardrails.steps.validate_governance.load_org_policy", return_value=None
        ),
        patch(
            "ai_guardrails.steps.validate_governance.load_team_policy",
            return_value=team,
        ),
    ):
        result = step.execute(ctx)
    assert result.status == "ok"
