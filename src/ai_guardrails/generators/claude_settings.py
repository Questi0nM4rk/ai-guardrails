"""ClaudeSettingsGenerator — generates .claude/settings.json.

Produces project-level Claude Code hooks + permission deny rules.
Deny rules are generated dynamically from GENERATED_CONFIGS constant
so they always cover all tamper-protected files.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ai_guardrails.constants import GENERATED_CONFIGS
from ai_guardrails.generators.base import compute_hash

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry

_HASH_PREFIX = "// ai-guardrails:hash:sha256:"


def _build_deny_rules() -> list[str]:
    """Build the list of Edit() deny rules from GENERATED_CONFIGS."""
    edit_rules = [f"Edit({cfg})" for cfg in sorted(GENERATED_CONFIGS)]
    bash_rules = [
        "Bash(* --no-verify *)",
        "Bash(git commit * -n *)",
        "Bash(git push --force *)",
        "Bash(git push * --force *)",
    ]
    return edit_rules + bash_rules


def _build_settings() -> dict:  # type: ignore[type-arg]
    return {
        "permissions": {
            "deny": _build_deny_rules(),
        },
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python -m ai_guardrails.hooks.dangerous_cmd",
                        }
                    ],
                }
            ]
        },
    }


class ClaudeSettingsGenerator:
    """Generates .claude/settings.json with deny rules and PreToolUse hooks."""

    name = "claude_settings"
    output_files = [".claude/settings.json"]

    def _build_body(self) -> str:
        settings = _build_settings()
        return json.dumps(settings, indent=2)

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/.claude/settings.json: content_with_hash_header}."""
        body = self._build_body()
        header = f"{_HASH_PREFIX}{compute_hash(body)}"
        full_content = f"{header}\n{body}\n"
        output_path = project_dir / ".claude" / "settings.json"
        return {output_path: full_content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if .claude/settings.json is missing or tampered."""
        target = project_dir / ".claude" / "settings.json"
        if not target.exists():
            return [".claude/settings.json is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        first_line = existing.split("\n", 1)[0].strip()
        if not first_line.startswith(_HASH_PREFIX):
            return [".claude/settings.json is stale or tampered — run: ai-guardrails generate"]
        stored_hash = first_line[len(_HASH_PREFIX) :]
        expected_body = self._build_body()
        if stored_hash != compute_hash(expected_body):
            return [".claude/settings.json is stale or tampered — run: ai-guardrails generate"]
        return []
