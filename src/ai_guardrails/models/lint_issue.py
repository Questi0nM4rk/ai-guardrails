"""LintIssue model — lint finding with content-hash fingerprint."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class LintIssue:
    """A single lint finding. Line is display-only — matching uses fingerprint."""

    rule: str
    linter: str
    file: str
    line: int  # display only, NOT used for matching
    col: int
    message: str
    fingerprint: str  # computed from content context, not line number

    @staticmethod
    def compute_fingerprint(
        rule: str,
        file: str,
        line_content: str,
        context_before: list[str],
        context_after: list[str],
    ) -> str:
        """SHA-256 of rule + file + stripped context. Stable across line moves."""
        parts = [rule, file]
        parts += [line.strip() for line in context_before[-2:]]
        parts += [line_content.strip()]
        parts += [line.strip() for line in context_after[:2]]
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
