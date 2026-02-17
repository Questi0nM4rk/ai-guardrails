"""Dangerous command checker for Claude Code PreToolUse hook.

Uses the Claude Code hook JSON protocol:
- Reads tool input from stdin JSON (``tool_input.command``)
- Outputs structured JSON on stdout with ``permissionDecision: "ask"``
- Always exits 0; every match escalates to the user permission prompt

All rules are defined in :data:`guardrails.constants.DANGEROUS_COMMANDS`.
"""

from __future__ import annotations

import json
import re
import sys

from guardrails.constants import DANGEROUS_COMMANDS, MatchType


def _match_rule(match_type: MatchType, pattern: str, command: str) -> bool:
    """Check if a single rule matches the command."""
    if match_type == "substring":
        return pattern in command
    if match_type == "regex":
        return bool(re.search(pattern, command))
    msg = f"Unknown match_type: {match_type!r}"
    raise ValueError(msg)


def check_command(command: str) -> list[str]:
    """Return all matching rule messages for a command."""
    return [
        message
        for match_type, pattern, message in DANGEROUS_COMMANDS
        if _match_rule(match_type, pattern, command)
    ]


def _read_command_from_stdin() -> str | None:
    """Read command from Claude Code hook JSON protocol on stdin."""
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command")
    except (json.JSONDecodeError, AttributeError, UnicodeDecodeError, OSError):
        return None


def _emit_ask(reasons: list[str]) -> int:
    """Emit JSON asking the user to approve or deny the command."""
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "; ".join(reasons),
                "additionalContext": (
                    "This command matched a dangerous pattern. "
                    "Do NOT retry with variations. "
                    "Ask the user if this operation is needed."
                ),
            },
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Reads command from stdin JSON (Claude Code protocol) or falls back
    to argv for backwards compatibility and testing.

    Always returns 0 (JSON protocol). Uses ``"ask"`` to escalate.
    """
    args = argv if argv is not None else sys.argv[1:]

    command: str | None = None
    if args:
        command = args[0]
    elif not sys.stdin.isatty():
        command = _read_command_from_stdin()

    if command is None:
        return 0

    matches = check_command(command)
    if matches:
        return _emit_ask(matches)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
