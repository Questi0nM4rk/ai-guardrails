"""Dangerous command checker for Claude Code PreToolUse hook.

Uses the Claude Code hook JSON protocol:
- Reads tool input from stdin JSON (``tool_input.command``)
- Outputs structured JSON on stdout with ``permissionDecision``
- Always exits 0 (JSON protocol); uses ``"ask"`` to escalate to user

All rules are defined in :data:`guardrails.constants.DANGEROUS_COMMANDS`.
"""

from __future__ import annotations

import json
import re
import sys

from guardrails.constants import DANGEROUS_COMMANDS


def _match_rule(match_type: str, pattern: str, command: str) -> bool:
    """Check if a single rule matches the command."""
    if match_type == "substring":
        return pattern in command
    if match_type == "regex":
        return bool(re.search(pattern, command))
    return False


def _check_blocked(command: str) -> str | None:
    """Return the first block-severity message, or ``None``."""
    for match_type, pattern, message, severity in DANGEROUS_COMMANDS:
        if severity == "block" and _match_rule(match_type, pattern, command):
            return message
    return None


def _check_warned(command: str) -> list[str]:
    """Return all warn-severity messages that match."""
    return [
        message
        for match_type, pattern, message, severity in DANGEROUS_COMMANDS
        if severity == "warn" and _match_rule(match_type, pattern, command)
    ]


def _read_command_from_stdin() -> str | None:
    """Read command from Claude Code hook JSON protocol on stdin."""
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command")
    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError, OSError):
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
