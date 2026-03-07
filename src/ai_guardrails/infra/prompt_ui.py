"""TTY detection and interactive prompt helpers."""

from __future__ import annotations

import sys


def is_tty() -> bool:
    """Return True if stdin and stdout are both interactive terminals."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def ask_yes_no(question: str, *, default: bool = True) -> bool:
    """Prompt the user with a Y/N question. Returns True for yes.

    Uses default if user hits Enter with no input.
    Raises EOFError if stdin is closed unexpectedly.
    """
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"  {question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")
