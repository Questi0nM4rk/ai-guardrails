"""Test that coverage requirements are consistently enforced at 85%."""

from __future__ import annotations

import re
from pathlib import Path


def test_ci_workflow_enforces_85_percent_coverage():
    """Verify CI workflow enforces 85% coverage threshold."""
    workflow_path = Path(".github/workflows/check.yml")
    content = workflow_path.read_text()

    # Check for --cov-fail-under=85
    assert "--cov-fail-under=85" in content, (
        "CI workflow should enforce 85% coverage with --cov-fail-under=85"
    )

    # Ensure no other coverage thresholds exist
    cov_fail_pattern = r"--cov-fail-under=(\d+)"
    matches = re.findall(cov_fail_pattern, content)
    assert matches == ["85"], f"Expected only 85% coverage threshold, found: {matches}"


def test_claude_md_documents_85_percent_coverage():
    """Verify CLAUDE.md documents 85% coverage requirement."""
    claude_md_path = Path("CLAUDE.md")
    content = claude_md_path.read_text()

    # Check for 85%+ test coverage statement
    assert "85%+ test coverage" in content, (
        "CLAUDE.md should document 85%+ test coverage requirement"
    )

    # Ensure no conflicting coverage percentages (like 80% or 90%)
    coverage_pattern = r"(\d+)%\+?\s+(?:test\s+)?coverage"
    matches = re.findall(coverage_pattern, content, re.IGNORECASE)
    assert "85" in matches, f"Expected 85% in coverage mentions, found: {matches}"
    assert "90" not in matches, "CLAUDE.md should not mention 90% coverage"
    assert "80" not in matches, "CLAUDE.md should not mention 80% coverage"


def test_no_conflicting_coverage_configs():
    """Verify no pytest.ini, .coveragerc, or other configs override coverage."""
    # These files could override --cov-fail-under in pytest
    conflicting_files = [
        "pytest.ini",
        ".coveragerc",
        "setup.cfg",
        "pyproject.toml",
    ]

    for filename in conflicting_files:
        path = Path(filename)
        if path.exists():
            content = path.read_text()
            # Check for fail_under or similar coverage config
            assert "fail_under" not in content, (
                f"{filename} should not override coverage threshold"
            )
            assert "min_coverage" not in content, (
                f"{filename} should not set minimum coverage"
            )
