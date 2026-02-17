"""Dangerous command checker for Claude Code PreToolUse hook.

Uses the Claude Code hook JSON protocol:
- Reads tool input from stdin JSON (``tool_input.command``)
- Outputs structured JSON on stdout with ``permissionDecision``
- Always exits 0 (JSON protocol); uses ``"ask"`` to escalate to user

Replaces lib/hooks/dangerous-command-check.sh.
"""

from __future__ import annotations

import json
import re
import sys

from guardrails.constants import BLOCKED_COMMANDS, WARNED_COMMANDS

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
)

# Force flags only warn on specific destructive commands
_FORCE_FLAG_COMMANDS = ("git push", "git reset", "docker rm")

# Regex-based warning patterns for destructive git operations
_SPECIAL_WARNS: tuple[tuple[str, str], ...] = (
    (r"git\s+reset\s+--hard\b", "git reset --hard discards uncommitted changes"),
    (
        r"git\s+checkout\s+(?:--\s+)?\.(?:\s*$|\s*&&|\s*;|\s*\|)",
        "git checkout . discards all unstaged changes",
    ),
    (
        r"git\s+restore\s+(?:--?\S+\s+)*\.(?:\s*$|\s*&&|\s*;|\s*\|)",
        "git restore . discards all unstaged changes",
    ),
    (
        r"git\s+clean\s+(?:-[a-zA-Z]*f|--force)",
        "git clean -f removes untracked files permanently",
    ),
    (
        r"git\s+branch\s+(?:-D\b|.*--delete\s+--force|.*--force\s+--delete)",
        "git branch -D force-deletes branch without merge check",
    ),
)


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

    # Regex-based destructive git operation warnings
    for regex, message in _SPECIAL_WARNS:
        if re.search(regex, command):
            warnings.append(message)

    # --force / -f only on specific destructive commands
    # Exclude --force-with-lease (has its own warning in WARNED_COMMANDS)
    has_force = ("--force" in command and "--force-with-lease" not in command) or bool(
        re.search(r"\s-f\b", command)
    )
    if has_force:
        for cmd_prefix in _FORCE_FLAG_COMMANDS:
            if cmd_prefix in command:
                warnings.append("Force flag on destructive operation")
                break

    return warnings


def _read_command_from_stdin() -> str | None:
    """Read command from Claude Code hook JSON protocol on stdin."""
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command")
    except (json.JSONDecodeError, AttributeError):
        return None


def _emit_ask(reason: str, *, blocked: bool) -> int:
    """Emit JSON asking the user to approve or deny the command.

    Both blocked and warned commands use ``"ask"`` so the user always
    sees the command in the permission prompt and decides themselves.
    """
    severity = "BLOCKED" if blocked else "WARNING"
    context = (
        "This command is blocked by security policy. "
        "Do NOT retry with variations. "
        "Ask the user if this operation is needed."
        if blocked
        else "This command may be destructive. The user should review it."
    )

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"{severity}: {reason}",
                "additionalContext": context,
            },
        },
        sys.stdout,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Reads command from stdin JSON (Claude Code protocol) or falls back
    to argv for backwards compatibility and testing.

    Always returns 0 (JSON protocol). Uses ``"ask"`` to escalate.
    """
    # Prefer argv for backwards compat, direct invocation, and testing
    args = argv if argv is not None else sys.argv[1:]

    command: str | None = None
    if args:
        command = args[0]
    elif not sys.stdin.isatty():
        # No argv — read from Claude Code hook JSON protocol on stdin
        command = _read_command_from_stdin()

    if command is None:
        return 0

    # Check blocked patterns first
    blocked_msg = _check_blocked(command)
    if blocked_msg is not None:
        return _emit_ask(blocked_msg, blocked=True)

    # Check warning patterns
    warnings = _check_warned(command)
    if warnings:
        return _emit_ask("; ".join(warnings), blocked=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
