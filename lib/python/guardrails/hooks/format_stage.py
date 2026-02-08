"""Format staged files and re-stage them.

Automatically fixes ALL auto-fixable issues in staged files and re-stages.
Ensures no context is wasted on syntax/formatting issues.

Replaces lib/hooks/format-and-stage.sh.
"""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path

# Extension -> list of (command, args) formatters
_FORMATTERS: dict[str, list[list[str]]] = {
    ".py": [
        ["ruff", "format"],
        ["ruff", "check", "--fix"],
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
}


def _git_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in result.stdout.splitlines() if f.strip()]


def _run_formatter(cmd: list[str], filepath: str) -> None:
    with contextlib.suppress(FileNotFoundError):
        subprocess.run(  # noqa: S603
            [*cmd, filepath],
            capture_output=True,
            text=True,
            check=False,
        )


def _git_add(filepath: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", "add", filepath],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    """Entry point. Formats staged files and re-stages them."""
    staged = _git_staged_files()
    if not staged:
        return 0

    for filepath in staged:
        if not Path(filepath).is_file():
            continue

        ext = Path(filepath).suffix
        formatters = _FORMATTERS.get(ext)
        if not formatters:
            continue

        for cmd in formatters:
            _run_formatter(cmd, filepath)

    # Re-stage all staged files (they may have been modified by formatters)
    for filepath in staged:
        if Path(filepath).is_file():
            _git_add(filepath)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
