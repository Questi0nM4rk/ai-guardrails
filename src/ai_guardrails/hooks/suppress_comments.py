"""Detect and reject lint/type suppression comments in staged files.

Philosophy: "Everything is an error or it's ignored."
Suppression comments create gray areas -- they are not allowed.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

from ai_guardrails.constants import (
    DOTFILE_MAP,
    SHEBANG_MAP,
    SUPPRESSION_PATTERNS,
    TEST_BASENAME_PATTERNS,
    TEST_PATH_SEGMENTS,
)

_MAX_VIOLATIONS_PER_PATTERN = 10
_DEFAULT_ALLOWLIST = ".suppression-allowlist"


def _is_test_file(filepath: str) -> bool:
    """Return True if *filepath* is in a test directory or is a test file."""
    normalized = filepath.replace("\\", "/")
    if any(segment in normalized for segment in TEST_PATH_SEGMENTS):
        return True
    # Check basename patterns against the filename only, not parent directories.
    # e.g. "/test_" should match "test_foo.py" but not a pytest tmpdir like
    # "/tmp/test_something/src.py".
    basename = "/" + Path(filepath).name
    return any(pattern in basename for pattern in TEST_BASENAME_PATTERNS)


def _infer_extension(filepath: str) -> str | None:  # ai-guardrails-allow: PLR0911, E501 "many branches" # fmt: skip
    """Infer language extension for *filepath* via suffix, dotfile map, or shebang."""
    path = Path(filepath)
    basename = path.name

    ext = path.suffix.lstrip(".")
    if ext and not basename.startswith("."):
        return ext

    if basename in DOTFILE_MAP:
        return DOTFILE_MAP[basename]

    try:
        with Path(filepath).open(encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
    except OSError:
        return None

    if first_line.startswith("#!"):
        for key, mapped_ext in SHEBANG_MAP.items():
            if key in first_line:
                return mapped_ext

    return None


def _load_allowlist(path: str = _DEFAULT_ALLOWLIST) -> list[str]:
    """Load regex patterns from the suppression allowlist file."""
    allowlist_path = Path(path)
    if not allowlist_path.is_file():
        return []

    patterns: list[str] = []
    for raw_line in allowlist_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _is_allowlisted(line_text: str, allowlist: list[str]) -> bool:
    """Return True if *line_text* matches any allowlist regex pattern."""
    for pattern in allowlist:
        try:
            if re.search(pattern, line_text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def _check_pattern_in_lines(
    filepath: str,
    lines: list[str],
    regex: str,
    desc: str,
    allowlist: list[str],
) -> int:
    """Check one suppression pattern across all lines of a file.

    Returns the number of violation groups found (0 or 1).
    """
    violation_lines: list[str] = []
    total_violations = 0
    for lineno, line in enumerate(lines, 1):
        if re.search(regex, line, re.IGNORECASE):
            match_text = f"{filepath}:{lineno}:{line}"
            if not _is_allowlisted(match_text, allowlist):
                total_violations += 1
                if len(violation_lines) < _MAX_VIOLATIONS_PER_PATTERN:
                    violation_lines.append(f"{lineno}:{line}")

    if not violation_lines:
        return 0

    print(f"ERROR: {desc} found in {filepath}")
    for vline in violation_lines:
        print(f"  {vline}")
    if total_violations > _MAX_VIOLATIONS_PER_PATTERN:
        hidden = total_violations - _MAX_VIOLATIONS_PER_PATTERN
        print(f"  ... and {hidden} more (showing first {_MAX_VIOLATIONS_PER_PATTERN})")
    print()
    return 1


def _check_file(filepath: str, allowlist: list[str]) -> int:
    """Check a single file for suppression comments.

    Returns the count of violation groups found.
    """
    if not Path(filepath).is_file() or _is_test_file(filepath):
        return 0

    ext = _infer_extension(filepath)
    if ext is None:
        return 0

    try:
        lines = (
            Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
        )
    except (OSError, UnicodeDecodeError):
        return 0

    count = 0
    for regex, desc, extensions in SUPPRESSION_PATTERNS:
        if ext in extensions:
            count += _check_pattern_in_lines(filepath, lines, regex, desc, allowlist)
    return count


def main(
    argv: list[str] | None = None, *, allowlist_path: str = _DEFAULT_ALLOWLIST
) -> int:
    """Entry point. Takes filenames as CLI args, returns 0 (clean) or 1 (violations)."""
    files = argv if argv is not None else sys.argv[1:]
    if not files:
        return 0

    allowlist = _load_allowlist(allowlist_path)
    suppression_pattern_count = sum(_check_file(f, allowlist) for f in files)

    if suppression_pattern_count > 0:
        print("========================================")
        print(f"Found {suppression_pattern_count} suppression pattern(s) across files")
        print("========================================")
        print()
        print("AI Guardrails philosophy: 'Everything is an error or it's ignored.'")
        print("Suppression comments create gray areas and are not allowed.")
        print()
        print("Options:")
        print("  1. Fix the underlying issue that triggered the lint/type error")
        print("  2. If the rule is wrong for this project, disable it in config")
        print("  3. For legitimate exceptions, add pattern to .suppression-allowlist")
        print("     (requires user approval and documented reason)")
        print()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
