"""ValidateGovernanceStep — enforce org/team locked rules and exception budgets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.infra.policy_loader import load_org_policy, load_team_policy
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.models.exception_record import ExceptionRecord
    from ai_guardrails.models.governance import OrgPolicy, TeamPolicy
    from ai_guardrails.pipelines.base import PipelineContext


class ValidateGovernanceStep:
    """Validate project exceptions against org and team governance policies.

    Checks:
    - No exception for a rule locked at org level.
    - No exception for a rule locked at team level.
    - Approved exception count does not exceed team budget.
    """

    name = "validate-governance"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        org = load_org_policy()
        team = load_team_policy(ctx.project_dir)

        exceptions = ctx.registry.exceptions if ctx.registry else []
        errors: list[str] = []
        errors.extend(_check_locked_rules(exceptions, org, team))
        errors.extend(_check_budget(exceptions, team))

        if errors:
            return StepResult(status="error", message="\n".join(errors))
        return StepResult(status="ok", message="Governance checks passed")


def _check_locked_rules(
    exceptions: list[ExceptionRecord],
    org: OrgPolicy | None,
    team: TeamPolicy | None,
) -> list[str]:
    errors: list[str] = []
    for exc in exceptions:
        if org:
            errors.extend(
                f"Rule {exc.rule!r} is locked at org level: {lock.reason}"
                for lock in org.locked_rules.values()
                if lock.rule == exc.rule
            )
        if team:
            errors.extend(
                f"Rule {exc.rule!r} is locked at team level: {lock.reason}"
                for lock in team.locked_rules.values()
                if lock.rule == exc.rule
            )
    return errors


def _check_budget(
    exceptions: list[ExceptionRecord], team: TeamPolicy | None
) -> list[str]:
    if team is None or team.exception_budget is None:
        return []
    approved_count = sum(1 for e in exceptions if e.is_approved)
    if approved_count > team.exception_budget:
        return [
            f"Exception budget exhausted: {approved_count} approved"
            f" > team limit of {team.exception_budget}"
        ]
    return []
