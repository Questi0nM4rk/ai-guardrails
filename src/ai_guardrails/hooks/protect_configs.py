"""Claude Code PreToolUse hook: protect generated and config files.

Prompts user approval before:
1. Editing auto-generated config files (hash header detected)
2. Editing .guardrails-exceptions.toml
3. Adding ignore patterns to config files
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ai_guardrails.constants import (
    CONFIG_FILES,
    GENERATED_CONFIGS,
    IGNORE_PATTERN,
    REGISTRY_FILENAME,
)
from ai_guardrails.hooks._utils import has_hash_header


def check_tool_input(
    tool_input: dict[str, str],
    *,
    project_dir: Path | None = None,
) -> str | None:
    """Check a tool input dict and return a reason string if access should be escalated.

    Returns None if the operation is allowed silently.
    ``project_dir`` defaults to the current working directory and is used to
    locate the registry file (hook is inactive when no registry is present).
    """
    cwd = project_dir if project_dir is not None else Path.cwd()
    registry_path = cwd / REGISTRY_FILENAME
    if not registry_path.is_file():
        return None

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return None

    path = Path(file_path)
    basename = path.name

    # Check 1: auto-generated config files (identified by hash header)
    if basename in GENERATED_CONFIGS and path.is_file() and has_hash_header(file_path):
        return (
            "This file is auto-generated from .guardrails-exceptions.toml "
            "by ai-guardrails generate. Direct edits will be overwritten on "
            "next run. Edit .guardrails-exceptions.toml instead, then run "
            "ai-guardrails generate. Explain why editing directly is the only solution."
        )

    # Check 2: the registry itself
    if basename == REGISTRY_FILENAME:
        return (
            "This is the single source of truth for all lint exceptions in "
            "this project. Every change MUST have a documented reason. "
            "Explain why this exception is necessary and cannot be fixed in the code."
        )

    # Check 3: ignore patterns being added to config files
    if basename in CONFIG_FILES:
        new_content = tool_input.get("new_string") or tool_input.get("content") or ""
        if new_content and re.search(IGNORE_PATTERN, new_content, re.IGNORECASE):
            return (
                f"Ignore pattern detected in {basename}. Lint exceptions must "
                "go in .guardrails-exceptions.toml, not directly in config files. "
                "Run ai-guardrails generate to apply changes. "
                "Explain why this is the only solution."
            )

    return None


def _emit_ask(reason: str) -> int:
    """Emit JSON escalating to user approval."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        },
    }
    print(json.dumps(output))
    return 0


def main() -> int:
    """Entry point. Reads JSON from stdin, emits decision to stdout."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError, ValueError):
        return 0

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return 0

    reason = check_tool_input(tool_input)
    if reason:
        return _emit_ask(reason)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
