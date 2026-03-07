"""SnapshotStep — capture current lint issues as a baseline."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.models.baseline import BaselineEntry, BaselineStatus
from ai_guardrails.pipelines.base import StepResult
from ai_guardrails.steps.check_step import CheckStep

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext

logger = logging.getLogger(__name__)

_DEFAULT_BASELINE = Path(".guardrails-baseline.json")


class SnapshotStep:
    """Runs linters, merges findings into the baseline, writes the result."""

    name = "snapshot"

    def __init__(self, baseline_file: Path, *, dry_run: bool = False) -> None:
        self._baseline_file = baseline_file
        self._dry_run = dry_run

    def validate(
        self,
        ctx: PipelineContext,  # ai-guardrails-allow: ARG002 "PipelineStep protocol"
    ) -> list[str]:
        """No preconditions."""
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Collect all current issues and merge them into the baseline file."""
        check = CheckStep(baseline_file=self._baseline_file)
        collected = check.collect_issues(ctx)
        issues = collected[0] if collected is not None else []

        # Load existing baseline
        existing: dict[str, BaselineEntry] = {}
        if self._baseline_file.exists():
            try:
                raw = json.loads(self._baseline_file.read_text())
                for entry in raw:
                    e = BaselineEntry.from_dict(entry)
                    existing[e.fingerprint] = e
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning(
                    "Baseline %s is corrupted, starting fresh: %s",
                    self._baseline_file,
                    exc,
                )

        today = datetime.datetime.now(tz=datetime.UTC).date()
        new_count = 0
        for issue in issues:
            if issue.fingerprint not in existing:
                existing[issue.fingerprint] = BaselineEntry(
                    rule=issue.rule,
                    fingerprint=issue.fingerprint,
                    file=issue.file,
                    status=BaselineStatus.LEGACY,
                    captured_at=today,
                )
                new_count += 1

        total = len(existing)
        old_count = total - new_count

        if self._dry_run:
            return StepResult(
                status="ok",
                message=(
                    f"Would capture {total} issue(s) "
                    f"({new_count} new, {old_count} existing). "
                    "Dry run — nothing written."
                ),
            )

        entries = [e.to_dict() for e in existing.values()]
        try:
            self._baseline_file.write_text(json.dumps(entries, indent=2) + "\n")
        except OSError as exc:
            return StepResult(
                status="error",
                message=f"Failed to write baseline {self._baseline_file}: {exc}",
            )

        return StepResult(
            status="ok",
            message=(
                f"Snapshot complete. {total} issue(s) captured "
                f"({new_count} new, {old_count} existing)."
            ),
        )
