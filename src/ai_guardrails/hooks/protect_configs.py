"""Protect generated config files — dual-mode hook.

**PreToolUse mode** (Claude Code): reads JSON from stdin, prompts user
approval before editing auto-generated configs, the registry, or adding
ignore patterns.

**Pre-commit mode** (lefthook): receives filenames as argv, verifies that
staged generated configs with hash headers have not been tampered with.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

from ai_guardrails.constants import (
    CONFIG_FILES,
    GENERATED_CONFIGS,
    IGNORE_PATTERN,
    REGISTRY_FILENAME,
)
from ai_guardrails.generators.base import compute_hash
from ai_guardrails.hooks._utils import has_hash_header


def check_tool_input(  # ai-guardrails-allow: PLR0911, E501 "multiple early-return guard clauses"
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


def _run_precommit(files: list[str]) -> int:
    """Pre-commit mode: verify staged generated configs have valid hashes."""
    violations = 0
    for filepath in files:
        path = Path(filepath)
        if path.name not in GENERATED_CONFIGS:
            continue
        if not path.is_file():
            continue
        if not has_hash_header(filepath):
            continue
        # Hash header present — verify body matches stored hash
        content = path.read_text()
        first_line, _, body = content.partition("\n")
        stored_hash = first_line.rsplit(":", 1)[-1].strip()
        actual_hash = compute_hash(body)
        if stored_hash != actual_hash:
            print(f"ERROR: {filepath} has been tampered with (hash mismatch).")
            print("  The hash header does not match the file content.")
            print("  Run: ai-guardrails generate")
            violations += 1
    return 1 if violations else 0


def _run_pretool_use() -> int:
    """PreToolUse mode: read JSON from stdin, emit decision to stdout."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError, ValueError):
        return 0

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return 0

    reason = check_tool_input(tool_input)
    return _emit_ask(reason) if reason else 0


def main() -> int:
    """Entry point. Handles both PreToolUse (stdin JSON) and pre-commit (argv)."""
    if len(sys.argv) > 1:
        return _run_precommit(sys.argv[1:])
    return _run_pretool_use()


if __name__ == "__main__":
    raise SystemExit(main())
