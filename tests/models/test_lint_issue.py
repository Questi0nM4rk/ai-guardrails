"""Tests for LintIssue — fingerprint stability and content sensitivity."""

from __future__ import annotations

import pytest

from ai_guardrails.models.lint_issue import LintIssue


def test_lint_issue_instantiation():
    fp = LintIssue.compute_fingerprint(
        "ruff/E501", "src/a.py", "x = very_long_line", [], []
    )
    issue = LintIssue(
        rule="ruff/E501",
        linter="ruff",
        file="src/a.py",
        line=42,
        col=1,
        message="Line too long (120 > 88)",
        fingerprint=fp,
    )
    assert issue.rule == "ruff/E501"
    assert issue.linter == "ruff"
    assert issue.file == "src/a.py"
    assert issue.line == 42
    assert issue.col == 1
    assert issue.message == "Line too long (120 > 88)"


def test_lint_issue_is_frozen():
    fp = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    issue = LintIssue(
        rule="ruff/E501",
        linter="ruff",
        file="src/a.py",
        line=1,
        col=1,
        message="msg",
        fingerprint=fp,
    )
    with pytest.raises(AttributeError):
        issue.line = 99  # type: ignore[misc]


def test_fingerprint_stable_across_line_moves():
    """Line number change does NOT affect fingerprint."""
    fp1 = LintIssue.compute_fingerprint(
        "ruff/E501",
        "src/a.py",
        "x = very_long_name",
        ["a = 1", "b = 2"],
        ["c = 3", "d = 4"],
    )
    # Same content, different line — fingerprint must be identical
    fp2 = LintIssue.compute_fingerprint(
        "ruff/E501",
        "src/a.py",
        "x = very_long_name",
        ["a = 1", "b = 2"],
        ["c = 3", "d = 4"],
    )
    assert fp1 == fp2


def test_fingerprint_changes_on_content_change():
    fp1 = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    fp2 = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 2", [], [])
    assert fp1 != fp2


def test_fingerprint_changes_on_rule_change():
    fp1 = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    fp2 = LintIssue.compute_fingerprint("ruff/E302", "src/a.py", "x = 1", [], [])
    assert fp1 != fp2


def test_fingerprint_changes_on_file_change():
    fp1 = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    fp2 = LintIssue.compute_fingerprint("ruff/E501", "src/b.py", "x = 1", [], [])
    assert fp1 != fp2


def test_fingerprint_changes_on_context_change():
    fp1 = LintIssue.compute_fingerprint(
        "ruff/E501", "src/a.py", "x = 1", ["before"], ["after"]
    )
    fp2 = LintIssue.compute_fingerprint(
        "ruff/E501", "src/a.py", "x = 1", ["different"], ["after"]
    )
    assert fp1 != fp2


def test_fingerprint_uses_only_last_2_before():
    """Only last 2 context_before lines matter."""
    fp1 = LintIssue.compute_fingerprint(
        "ruff/E501",
        "src/a.py",
        "x = 1",
        ["ignored", "a = 1", "b = 2"],  # 3 lines, first ignored
        [],
    )
    fp2 = LintIssue.compute_fingerprint(
        "ruff/E501",
        "src/a.py",
        "x = 1",
        ["also_ignored", "a = 1", "b = 2"],  # 3 lines, first different but ignored
        [],
    )
    assert fp1 == fp2


def test_fingerprint_uses_only_first_2_after():
    """Only first 2 context_after lines matter."""
    fp1 = LintIssue.compute_fingerprint(
        "ruff/E501",
        "src/a.py",
        "x = 1",
        [],
        ["c = 3", "d = 4", "ignored"],  # 3 lines, last ignored
    )
    fp2 = LintIssue.compute_fingerprint(
        "ruff/E501",
        "src/a.py",
        "x = 1",
        [],
        ["c = 3", "d = 4", "also_ignored"],  # 3 lines, last different but ignored
    )
    assert fp1 == fp2


def test_fingerprint_strips_whitespace():
    """Leading/trailing whitespace stripped before hashing."""
    fp1 = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "  x = 1  ", [], [])
    fp2 = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    assert fp1 == fp2


def test_fingerprint_length():
    """Fingerprint is 16 hex chars (64-bit prefix of SHA-256)."""
    fp = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)


def test_lint_issue_equality():
    fp = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    issue1 = LintIssue(
        rule="ruff/E501",
        linter="ruff",
        file="src/a.py",
        line=1,
        col=1,
        message="msg",
        fingerprint=fp,
    )
    issue2 = LintIssue(
        rule="ruff/E501",
        linter="ruff",
        file="src/a.py",
        line=1,
        col=1,
        message="msg",
        fingerprint=fp,
    )
    assert issue1 == issue2


def test_lint_issue_hashable():
    """LintIssue can be used in a set (frozen dataclass)."""
    fp = LintIssue.compute_fingerprint("ruff/E501", "src/a.py", "x = 1", [], [])
    issue = LintIssue(
        rule="ruff/E501",
        linter="ruff",
        file="src/a.py",
        line=1,
        col=1,
        message="msg",
        fingerprint=fp,
    )
    s = {issue}
    assert issue in s
