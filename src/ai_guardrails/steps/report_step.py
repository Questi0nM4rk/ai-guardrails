"""ReportStep — reads .guardrails-audit.jsonl and prints a summary."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext

_AUDIT_FILE = ".guardrails-audit.jsonl"
_MAX_ROWS = 10


class ReportStep:
    """Reads the audit log and prints a summary of recent check runs."""

    name = "report"

    def validate(
        self,
        ctx: PipelineContext,  # ai-guardrails-allow: ARG002 "PipelineStep protocol"
    ) -> list[str]:
        """No preconditions required."""
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Read audit log and print last _MAX_ROWS entries."""
        audit_path = ctx.project_dir / _AUDIT_FILE
        if not audit_path.exists():
            ctx.console.info("No audit log found. Run 'ai-guardrails check' first.")
            return StepResult(status="ok", message="No audit log found.")

        lines = audit_path.read_text(encoding="utf-8").splitlines()
        rows = []
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError:
                continue

        recent = rows[-_MAX_ROWS:]
        ctx.console.info(f"Last {len(recent)} check run(s):")
        for row in recent:
            ts = row.get("timestamp", "?")[:19]
            status = row.get("status", "?")
            new_issues = row.get("new_issues", 0)
            ctx.console.info(f"  {ts}  {status:<6}  {new_issues} new issue(s)")

        return StepResult(status="ok", message=f"Showed {len(recent)} audit record(s).")
