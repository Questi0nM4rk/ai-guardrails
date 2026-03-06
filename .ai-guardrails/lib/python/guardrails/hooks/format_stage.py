"""Format staged files and re-stage them.

Automatically fixes ALL auto-fixable issues in staged files and re-stages.
Ensures no context is wasted on syntax/formatting issues.

Replaces lib/hooks/format-and-stage.sh.
"""

from __future__ import annotations

import contextlib
import hashlib
import subprocess
from pathlib import Path

# Extension -> list of (command, args) formatters
_FORMATTERS: dict[str, list[list[str]]] = {
    ".py": [
        ["ruff", "check", "--fix"],
        ["ruff", "format"],
    ],
    ".sh": [
        ["shfmt", "-w", "-i", "2", "-ci", "-bn"],
    ],
    ".bash": [
        ["shfmt", "-w", "-i", "2", "-ci", "-bn"],
    ],
    ".md": [
        ["markdownlint-cli2", "--fix"],
    ],
    ".ts": [
        ["biome", "check", "--write"],
    ],
    ".tsx": [
        ["biome", "check", "--write"],
    ],
    ".js": [
        ["biome", "check", "--write"],
    ],
    ".jsx": [
        ["biome", "check", "--write"],
    ],
    ".json": [
        ["biome", "check", "--write"],
    ],
    ".toml": [
        ["taplo", "format"],
    ],
    ".rs": [
        ["rustfmt"],
    ],
    ".lua": [
        ["stylua"],
    ],
    ".go": [
        ["gofmt", "-w"],
    ],
    ".c": [
        ["clang-format", "-i"],
    ],
    ".cpp": [
        ["clang-format", "-i"],
    ],
    ".cc": [
        ["clang-format", "-i"],
    ],
    ".cxx": [
        ["clang-format", "-i"],
    ],
    ".h": [
        ["clang-format", "-i"],
    ],
    ".hpp": [
        ["clang-format", "-i"],
    ],
}


def _git_staged_files() -> list[str]:
    """Return list of staged filenames (Added/Copied/Modified only).

    Returns an empty list if the git command fails (e.g. not a git repo).
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.splitlines() if f.strip()]


def _run_formatter(cmd: list[str], filepath: str) -> None:
    """Run a single formatter command on *filepath*, silently skipping if not installed."""
    with contextlib.suppress(FileNotFoundError):
        subprocess.run(
            [*cmd, filepath],
            capture_output=True,
            text=True,
            check=False,
        )


def _git_add(filepath: str) -> None:
    """Stage a single file with ``git add``."""
    subprocess.run(
        ["git", "add", filepath],
        capture_output=True,
        text=True,
        check=False,
    )


def _detect_shell_by_shebang(filepath: str) -> bool:
    """Return True if the file starts with a shell shebang (``#!/bin/sh``, etc.)."""
    try:
        with Path(filepath).open("rb") as f:
            first_line = f.readline(128)
    except OSError:
        return False
    if not first_line.startswith(b"#!"):
        return False
    shells = (b"/sh", b"/bash", b"/zsh", b"/ash", b"/dash")
    # Match both "/bin/bash" and "/usr/bin/env bash" patterns
    return any(s in first_line for s in shells) or any(
        b" " + s.lstrip(b"/") in first_line for s in shells
    )


def _file_hash(filepath: str) -> str | None:
    """Return SHA-256 hex digest of file contents, or None if unreadable."""
    try:
        return hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
    except OSError:
        return None


def main() -> int:
    """Entry point. Formats staged files and re-stages them."""
    staged = _git_staged_files()
    if not staged:
        return 0

    # Snapshot file hashes before formatting
    hashes_before: dict[str, str | None] = {}
    for filepath in staged:
        if Path(filepath).is_file():
            hashes_before[filepath] = _file_hash(filepath)

    for filepath in staged:
        if not Path(filepath).is_file():
            continue

        ext = Path(filepath).suffix
        formatters = _FORMATTERS.get(ext)
        if not formatters and _detect_shell_by_shebang(filepath):
            formatters = _FORMATTERS[".sh"]
        if not formatters:
            continue

        for cmd in formatters:
            _run_formatter(cmd, filepath)

    # Only re-stage files that were actually modified by formatters
    for filepath in staged:
        if not Path(filepath).is_file():
            continue
        hash_after = _file_hash(filepath)
        if hash_after != hashes_before.get(filepath):
            _git_add(filepath)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
