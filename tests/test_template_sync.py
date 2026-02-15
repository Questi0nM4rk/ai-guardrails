"""Test that template files stay in sync with deployed copies."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent


def _extract_prompt(wf: dict) -> str | None:
    """Extract the prompt field from a workflow's steps."""
    jobs = wf.get("jobs", {})
    if not jobs:
        return None
    steps = next(iter(jobs.values())).get("steps", [])
    for step in steps:
        prompt = step.get("with", {}).get("prompt")
        if prompt is not None:
            return prompt
    return None


class TestClaudeReviewSync:
    """Ensure .github/ and templates/ Claude review prompts stay in sync."""

    def test_claude_review_prompt_sync(self) -> None:
        """Verify .github/ and templates/ Claude review prompts match."""
        github_wf_path = ROOT / ".github" / "workflows" / "claude-code-review.yml"
        template_wf_path = ROOT / "templates" / "workflows" / "claude-review.yml"

        if not github_wf_path.exists() or not template_wf_path.exists():
            pytest.skip("Workflow files not found")

        github_wf = yaml.safe_load(github_wf_path.read_text())
        template_wf = yaml.safe_load(template_wf_path.read_text())

        github_prompt = _extract_prompt(github_wf)
        template_prompt = _extract_prompt(template_wf)

        if github_prompt is None or template_prompt is None:
            pytest.skip("Could not find prompt in workflow files")

        assert github_prompt == template_prompt, (
            "Claude review prompts have drifted between .github/ and templates/"
        )
