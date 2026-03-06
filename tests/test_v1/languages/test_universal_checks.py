"""Tests for _universal_checks helpers — direct unit tests."""

from __future__ import annotations

from pathlib import Path


def test_check_claude_settings_missing_file(tmp_path: Path) -> None:
    """check_claude_settings returns issue when file is missing."""
    from ai_guardrails.languages._universal_checks import check_claude_settings

    issues = check_claude_settings(tmp_path)
    assert len(issues) == 1
    assert "missing" in issues[0]
