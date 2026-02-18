"""Test that template files stay in sync with deployed copies."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent


def _extract_prompt(wf: dict) -> str | None:
    """Extract the prompt field from a workflow's steps.

    Iterates all jobs to handle ordering changes.
    """
    jobs = wf.get("jobs", {})
    for job in jobs.values():
        for step in job.get("steps", []):
            prompt = step.get("with", {}).get("prompt")
            if prompt is not None:
                return prompt
    return None


def _extract_rev_pins(text: str) -> dict[str, str]:
    """Extract repo URL to rev mappings from a YAML string.

    Returns dict like ``{"https://github.com/foo/bar": "v1.2.3"}``.
    """
    revs: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        repo_match = re.match(r"\s*-\s*repo:\s*(https://\S+)", line)
        if repo_match:
            repo_url = repo_match.group(1)
            # Look for rev: on the next line
            if i + 1 < len(lines):
                rev_match = re.match(r'\s*rev:\s*["\'\']?([^"\'\'\s]+)["\'\']?', lines[i + 1])
                if rev_match:
                    revs[repo_url] = rev_match.group(1)
    return revs


def test_claude_review_prompt_sync() -> None:
    """Verify .github/ and templates/ Claude review prompts match."""
    github_wf_path = ROOT / ".github" / "workflows" / "claude-code-review.yml"
    template_wf_path = ROOT / "templates" / "workflows" / "claude-review.yml"

    if not github_wf_path.exists() or not template_wf_path.exists():
        pytest.skip("Workflow files not found")

    github_wf = yaml.safe_load(github_wf_path.read_text())
    template_wf = yaml.safe_load(template_wf_path.read_text())

    if not isinstance(github_wf, dict) or not isinstance(template_wf, dict):
        pytest.skip("Workflow files are empty or not valid YAML mappings")

    github_prompt = _extract_prompt(github_wf)
    template_prompt = _extract_prompt(template_wf)

    if github_prompt is None or template_prompt is None:
        pytest.skip("Could not find prompt in workflow files")

    assert github_prompt == template_prompt, (
        "Claude review prompts have drifted between .github/ and templates/"
    )


def test_precommit_hook_revisions_match_templates() -> None:
    """Verify all rev: pins in templates match the project .pre-commit-config.yaml.

    The project config is the source of truth. Templates must not drift behind.
    """
    source_config = ROOT / ".pre-commit-config.yaml"
    template_dir = ROOT / "templates" / "pre-commit"

    if not source_config.exists():
        pytest.skip(".pre-commit-config.yaml not found")
    if not template_dir.is_dir():
        pytest.skip("templates/pre-commit/ not found")

    source_revs = _extract_rev_pins(source_config.read_text())

    drifted: list[str] = []
    for template_file in sorted(template_dir.glob("*.yaml")):
        template_revs = _extract_rev_pins(template_file.read_text())
        for repo_url, template_rev in template_revs.items():
            if repo_url in source_revs:
                source_rev = source_revs[repo_url]
                if template_rev != source_rev:
                    drifted.append(
                        f"  {template_file.name}: {repo_url}\n"
                        f"    template={template_rev}  source={source_rev}"
                    )

    assert not drifted, "Template pre-commit revisions have drifted from source:\n" + "\n".join(
        drifted
    )


def test_template_node_version_matches_source() -> None:
    """Verify the default node version in base.yaml matches the project config."""
    source_config = ROOT / ".pre-commit-config.yaml"
    base_template = ROOT / "templates" / "pre-commit" / "base.yaml"

    if not source_config.exists() or not base_template.exists():
        pytest.skip("Config files not found")

    source_data = yaml.safe_load(source_config.read_text())
    template_data = yaml.safe_load(base_template.read_text())

    source_node = source_data.get("default_language_version", {}).get("node")
    template_node = template_data.get("default_language_version", {}).get("node")

    if source_node is None or template_node is None:
        pytest.skip("Node version not configured")

    assert str(template_node) == str(source_node), (
        f"base.yaml node version ({template_node}) != source ({source_node})"
    )
