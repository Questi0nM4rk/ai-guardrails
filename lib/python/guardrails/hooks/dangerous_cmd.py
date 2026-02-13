"""Dangerous command checker for Claude Code PreToolUse hook.

Blocks (exit 2) or warns (exit 0 with message) on dangerous bash commands.
Exit 0 = allow, Exit 2 = block.

Claude Code PreToolUse hooks receive JSON on stdin::

    {"tool_name": "Bash", "tool_input": {"command": "..."}}

Block/warn messages go to stderr (Claude Code feeds stderr back on exit 2).
Falls back to ``sys.argv[1]`` for direct CLI testing.
"""

from __future__ import annotations

import json
import re
import sys

from guardrails.constants import (
    BLOCKED_COMMANDS,
    NC,
    RED,
    WARNED_COMMANDS,
    YELLOW,
)

# Special-case block patterns not covered by simple substring matching
_SPECIAL_BLOCKS: tuple[tuple[str, str], ...] = (
    # git commit -n (short for --no-verify)
    (
        r"git\s+commit\b.*\s-n\b",
        "git commit -n is short for --no-verify.\n"
        "  This is never allowed. Fix the issue that's "
        "causing hooks to fail.",
    ),
    # dd writing to block device
    (r"dd\s+if=.*of=/dev/", "Refusing to write directly to block device"),
    # gh --admin bypasses branch protection
    (
        r"\bgh\s+.*--admin\b",
        "--admin bypasses branch protection rules.\n"
        "  This requires explicit user approval. Ask before using.",
    ),
)

# Force flags only warn on specific destructive commands
_FORCE_FLAG_COMMANDS = ("git push", "git reset", "docker rm")


def _check_blocked(command: str) -> str | None:
    for pattern, message in BLOCKED_COMMANDS:
        if pattern in command:
            return message

    for regex, message in _SPECIAL_BLOCKS:
        if re.search(regex, command):
            return message

    return None


def _check_warned(command: str) -> list[str]:
    warnings: list[str] = []

    for pattern, message in WARNED_COMMANDS:
        if pattern in command:
            warnings.append(message)

    # --force / -f only on specific destructive commands
    if "--force" in command or re.search(r"\s-f\b", command):
        for cmd_prefix in _FORCE_FLAG_COMMANDS:
            if cmd_prefix in command:
                warnings.append("Force flag on destructive operation")
                break

    return warnings


def _read_command_from_stdin() -> str:
    """Read command from Claude Code PreToolUse JSON on stdin."""
    try:
        data = json.load(sys.stdin)
        return str(data.get("tool_input", {}).get("command", ""))
    except (json.JSONDecodeError, AttributeError):
        return ""


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Reads command from stdin JSON (Claude Code protocol) or argv[1] for
    direct testing. Returns 0 (allow) or 2 (block).
    """
    args = argv if argv is not None else sys.argv[1:]

    command = args[0] if args else _read_command_from_stdin()

    if not command:
        return 0

    # Check blocked patterns first
    blocked_msg = _check_blocked(command)
    if blocked_msg is not None:
        print(f"{RED}BLOCKED:{NC} {blocked_msg}", file=sys.stderr)
        return 2

    # Check warning patterns
    warnings = _check_warned(command)
    for msg in warnings:
        print(f"{YELLOW}WARNING:{NC} {msg}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
