"""Test that coverage requirements are consistently enforced at 85%."""

from __future__ import annotations

import re
from pathlib import Path

import tomllib  # Python 3.11+


def test_ci_workflow_enforces_85_percent_coverage() -> None:
    """Verify CI workflow enforces 85% coverage threshold."""
    workflow_path = Path(".github/workflows/check.yml")
    content = workflow_path.read_text()

    # Check for --cov-fail-under=85
    assert "--cov-fail-under=85" in content, (
        "CI workflow should enforce 85% coverage with --cov-fail-under=85"
    )

    # Ensure all coverage thresholds are 85%
    cov_fail_pattern = r"--cov-fail-under=(\d+)"
    matches = re.findall(cov_fail_pattern, content)
    assert matches, "Expected at least one --cov-fail-under in workflow"
    assert all(m == "85" for m in matches), (
        f"All coverage thresholds should be 85%, found: {matches}"
    )


def test_claude_md_documents_85_percent_coverage() -> None:
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


def test_no_conflicting_coverage_configs() -> None:
    """Verify no pytest.ini, .coveragerc, or other configs override coverage."""
    # Plain text configs - simple substring check
    plaintext_configs = ["pytest.ini", ".coveragerc", "setup.cfg"]

    for filename in plaintext_configs:
        path = Path(filename)
        if path.exists():
            content = path.read_text()
            assert "fail_under" not in content, f"{filename} should not override coverage threshold"
            assert "min_coverage" not in content, f"{filename} should not set minimum coverage"

    # pyproject.toml - parse and check specific keys to avoid false positives
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        # Check tool.coverage.report.fail_under
        coverage_report = data.get("tool", {}).get("coverage", {}).get("report", {})
        assert "fail_under" not in coverage_report, (
            "pyproject.toml [tool.coverage.report] should not set fail_under"
        )

        # Check tool.pytest.ini_options for coverage settings
        pytest_opts = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
        addopts = pytest_opts.get("addopts", "")

        # Handle addopts as either string or list
        if isinstance(addopts, list):
            addopts_str = " ".join(addopts)
        else:
            addopts_str = addopts

        assert "--cov-fail-under" not in addopts_str, (
            "pyproject.toml [tool.pytest.ini_options] should not set --cov-fail-under"
        )
