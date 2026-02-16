"""Dangerous command checker for Claude Code ExecTool hook.

Blocks (exit 2) or warns (exit 0 with message) on dangerous bash commands.
Exit 0 = allow, Exit 2 = block.

Replaces lib/hooks/dangerous-command-check.sh.
"""

from __future__ import annotations

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


def main(argv: list[str] | None = None) -> int:
    """Entry point. Takes command string as first arg.

    Returns 0 (allow) or 2 (block).
    """
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        return 0

    command = args[0]

    # Check blocked patterns first
    blocked_msg = _check_blocked(command)
    if blocked_msg is not None:
        print(f"{RED}BLOCKED:{NC} {blocked_msg}")
        return 2

    # Check warning patterns
    warnings = _check_warned(command)
    for msg in warnings:
        print(f"{YELLOW}WARNING:{NC} {msg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
