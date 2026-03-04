"""Format staged files and re-stage them.

Automatically fixes all auto-fixable issues in staged files and re-stages.
Ensures no context is wasted on syntax/formatting issues.
"""

from __future__ import annotations

import contextlib
import hashlib
from pathlib import Path
import subprocess

# Extension -> list of (command, args_prefix) formatters.
# Each entry is a list where the first element is the tool name and remaining
# elements are flags; the filepath is appended when the formatter is called.
FORMATTERS: dict[str, list[list[str]]] = {
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
    ".jsonc": [
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
    """Return list of staged filenames (Added/Copied/Modified only)."""
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
    """Run a single formatter on *filepath*, silently skipping if not installed."""
    with contextlib.suppress(FileNotFoundError):
        subprocess.run(
            [*cmd, filepath],
            capture_output=True,
            text=True,
            check=False,
        )


def _git_add(filepath: str) -> None:
    """Stage a single file with git add."""
    subprocess.run(
        ["git", "add", filepath],
        capture_output=True,
        text=True,
        check=False,
    )


def _detect_shell_by_shebang(filepath: str) -> bool:
    """Return True if the file starts with a shell shebang."""
    try:
        with Path(filepath).open("rb") as f:
            first_line = f.readline(128)
    except OSError:
        return False
    if not first_line.startswith(b"#!"):
        return False
    shells = (b"/sh", b"/bash", b"/zsh", b"/ash", b"/dash")
    return any(s in first_line for s in shells) or any(
        b" " + s.lstrip(b"/") in first_line for s in shells
    )


def _file_hash(filepath: str) -> str | None:
    """Return SHA-256 hex digest of file contents, or None if unreadable."""
    try:
        return hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
    except OSError:
        return None


def _formatters_for(filepath: str) -> list[list[str]] | None:
    """Return formatter commands for *filepath*, or None if unsupported."""
    ext = Path(filepath).suffix
    formatters = FORMATTERS.get(ext)
    if not formatters and _detect_shell_by_shebang(filepath):
        formatters = FORMATTERS[".sh"]
    return formatters


def _format_file(filepath: str) -> None:
    """Run all applicable formatters on a single file."""
    formatters = _formatters_for(filepath)
    if not formatters:
        return
    for cmd in formatters:
        _run_formatter(cmd, filepath)


def _restage_if_changed(filepath: str, hash_before: str | None) -> None:
    """Re-stage *filepath* if its content changed since *hash_before*."""
    if not Path(filepath).is_file():
        return
    if _file_hash(filepath) != hash_before:
        _git_add(filepath)


def main() -> int:
    """Entry point. Formats staged files and re-stages modified ones."""
    staged = _git_staged_files()
    if not staged:
        return 0

    hashes_before = {f: _file_hash(f) for f in staged if Path(f).is_file()}

    for filepath in staged:
        if Path(filepath).is_file():
            _format_file(filepath)

    for filepath in staged:
        _restage_if_changed(filepath, hashes_before.get(filepath))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
