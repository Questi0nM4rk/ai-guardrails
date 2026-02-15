"""Test that template files stay in sync with deployed copies."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent


class TestClaudeReviewSync:
    """Ensure .github/ and templates/ Claude review prompts stay in sync."""

    def test_claude_review_prompt_sync(self) -> None:
        """Ensure .github/ and templates/ Claude review prompts are identical."""
        github_wf_path = ROOT / ".github" / "workflows" / "claude-code-review.yml"
        template_wf_path = ROOT / "templates" / "workflows" / "claude-review.yml"

        if not github_wf_path.exists() or not template_wf_path.exists():
            pytest.skip("Workflow files not found")

        github_wf = yaml.safe_load(github_wf_path.read_text())
        template_wf = yaml.safe_load(template_wf_path.read_text())

        # Extract prompt from the last step's 'with.prompt'
        github_steps = next(iter(github_wf["jobs"].values()))["steps"]
        template_steps = next(iter(template_wf["jobs"].values()))["steps"]

        github_prompt = None
        template_prompt = None

        for step in github_steps:
            if "with" in step and "prompt" in step.get("with", {}):
                github_prompt = step["with"]["prompt"]

        for step in template_steps:
            if "with" in step and "prompt" in step.get("with", {}):
                template_prompt = step["with"]["prompt"]

        if github_prompt is None or template_prompt is None:
            pytest.skip("Could not find prompt in workflow files")

        assert github_prompt == template_prompt, (
            "Claude review prompts have drifted between .github/ and templates/"
        )
