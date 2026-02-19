"""Test that template files stay in sync with deployed copies."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_claude_review_workflow_removed() -> None:
    """Claude auto-review workflows were removed; files should not exist."""
    assert not (ROOT / ".github" / "workflows" / "claude-code-review.yml").exists()
    assert not (ROOT / "templates" / "workflows" / "claude-review.yml").exists()
