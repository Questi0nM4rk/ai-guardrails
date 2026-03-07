"""CheckStep — run linters and compare results against a baseline snapshot.

Implements hold-the-line enforcement: new issues block with status='error',
issues already recorded in the baseline are suppressed.

Supported linters:
  Python: ruff check --output-format=json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.hooks.allow_comment import (
    get_bare_allowed_rules,
    parse_allow_comment,
)
from ai_guardrails.models.baseline import BaselineEntry, BaselineStatus
from ai_guardrails.models.lint_issue import LintIssue
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext

logger = logging.getLogger(__name__)

_DEFAULT_BASELINE = Path(".guardrails-baseline.json")


def _read_lines(file_path: str) -> list[str]:
    """Read source lines from a file; return empty list on any error."""
    try:
        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        return text.splitlines()
    except OSError:
        return []


_MAX_INLINE_ISSUES = 5


class CheckStep:
    """Runs linters and compares findings against a baseline snapshot."""

    name = "check"

    def __init__(self, baseline_file: Path = _DEFAULT_BASELINE) -> None:
        self._baseline_file = baseline_file
        self.new_issues: list[LintIssue] = []

    def validate(
        self,
        ctx: PipelineContext,  # ai-guardrails-allow: ARG002 "PipelineStep protocol"
    ) -> list[str]:
        """No preconditions — baseline absence is handled gracefully in execute."""
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Run configured linters; return error if new issues found."""
        collected = self._collect_issues(ctx)
        if collected is None:
            return StepResult(status="skip", message="No supported languages detected")

        issues, allow_count = collected

        baseline = self._load_baseline()
        active_fps = {
            e.fingerprint
            for e in baseline
            if e.status in (BaselineStatus.LEGACY, BaselineStatus.BURN_DOWN)
        }

        new_issues = [i for i in issues if i.fingerprint not in active_fps]
        self.new_issues = new_issues
        known_count = len(issues) - len(new_issues)

        if new_issues:
            summary = ", ".join(
                f"{i.rule}@{i.file}:{i.line}" for i in new_issues[:_MAX_INLINE_ISSUES]
            )
            extra = len(new_issues) - _MAX_INLINE_ISSUES
            suffix = f" (and {extra} more)" if extra > 0 else ""
            return StepResult(
                status="error",
                message=(f"{len(new_issues)} new issue(s) found: {summary}{suffix}"),
            )

        parts: list[str] = []
        if known_count:
            parts.append(f"{known_count} known baseline issue(s) suppressed.")
        if allow_count:
            parts.append(f"{allow_count} suppressed by ai-guardrails-allow.")

        if parts:
            return StepResult(status="ok", message="No new issues. " + " ".join(parts))
        return StepResult(status="ok", message="No issues found.")

    def collect_issues(
        self, ctx: PipelineContext
    ) -> tuple[list[LintIssue], int] | None:
        """Public wrapper — same as _collect_issues, callable without SLF001."""
        return self._collect_issues(ctx)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_issues(
        self, ctx: PipelineContext
    ) -> tuple[list[LintIssue], int] | None:
        """Return lint issues and allow-suppressed count, or None if unsupported."""
        issues: list[LintIssue] = []
        allow_count = 0
        supported = False

        for plugin in ctx.languages:
            if plugin.key == "python":
                supported = True
                plugin_issues, plugin_allow_count = self._run_ruff(ctx)
                issues.extend(plugin_issues)
                allow_count += plugin_allow_count

        return (issues, allow_count) if supported else None

    def _run_ruff(  # ai-guardrails-allow: PLR0915, E501 "ruff output parsing has many required branches"
        self, ctx: PipelineContext
    ) -> tuple[list[LintIssue], int]:
        """Invoke ruff and parse JSON output into LintIssue list."""
        result = ctx.command_runner.run(
            [
                "uv",
                "run",
                "ruff",
                "check",
                "--output-format=json",
                str(ctx.project_dir),
            ],
            cwd=ctx.project_dir,
        )

        if not result.stdout.strip():
            return [], 0

        try:
            raw = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning("ruff produced non-JSON output: %s", result.stdout[:200])
            return [], 0

        issues: list[LintIssue] = []
        allow_count = 0
        for item in raw:
            rule = item.get("code") or "unknown"
            file_path = item.get("filename", "")
            location = item.get("location", {})
            line = location.get("row", 0)
            col = location.get("column", 0)
            message = item.get("message", "")

            # Read source lines for content-stable fingerprinting.
            # Falls back to empty strings if the file cannot be read.
            src_lines = _read_lines(file_path)
            line_idx = max(0, line - 1)
            line_content = src_lines[line_idx] if line_idx < len(src_lines) else ""
            context_before = src_lines[max(0, line_idx - 2) : line_idx]
            context_after = src_lines[line_idx + 1 : line_idx + 3]

            fingerprint = LintIssue.compute_fingerprint(
                rule=rule,
                file=file_path,
                line_content=line_content,
                context_before=context_before,
                context_after=context_after,
            )

            allowed = parse_allow_comment(line_content)
            if rule in allowed:
                allow_count += 1
                continue

            bare = get_bare_allowed_rules(line_content)
            if rule in bare:
                # Bare allow comment (no reason) → report AI001 instead of original rule
                ai_fp = LintIssue.compute_fingerprint(
                    rule="AI001",
                    file=file_path,
                    line_content=line_content,
                    context_before=context_before,
                    context_after=context_after,
                )
                issues.append(
                    LintIssue(
                        rule="AI001",
                        linter="ai-guardrails",
                        file=file_path,
                        line=line,
                        col=col,
                        message=(
                            f'ai-guardrails-allow on "{rule}": '
                            'missing quoted reason — add "reason text"'
                        ),
                        fingerprint=ai_fp,
                    )
                )
                continue

            issues.append(
                LintIssue(
                    rule=rule,
                    linter="ruff",
                    file=file_path,
                    line=line,
                    col=col,
                    message=message,
                    fingerprint=fingerprint,
                )
            )

        return issues, allow_count

    def _load_baseline(self) -> list[BaselineEntry]:
        """Load baseline entries from JSON file. Returns empty list if absent."""
        if not self._baseline_file.exists():
            return []

        try:
            raw = json.loads(self._baseline_file.read_text())
            return [BaselineEntry.from_dict(entry) for entry in raw]
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to parse baseline %s: %s", self._baseline_file, exc)
            return []
