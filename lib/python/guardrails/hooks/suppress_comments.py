"""Detect and reject lint/type suppression comments in staged files.

Philosophy: "Everything is an error or it's ignored."
Suppression comments create gray areas -- they are not allowed.

Replaces lib/hooks/detect-suppression-comments.sh.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from guardrails.constants import (
    DOTFILE_MAP,
    NC,
    RED,
    SHEBANG_MAP,
    SUPPRESSION_PATTERNS,
    TEST_BASENAME_PATTERNS,
    TEST_PATH_SEGMENTS,
    YELLOW,
)

_MAX_VIOLATIONS_PER_PATTERN = 10


def _is_test_file(filepath: str) -> bool:
    return any(segment in filepath for segment in TEST_PATH_SEGMENTS) or any(
        pattern in filepath for pattern in TEST_BASENAME_PATTERNS
    )


def _infer_extension(filepath: str) -> str | None:
    path = Path(filepath)
    basename = path.name

    # Normal extension
    ext = path.suffix.lstrip(".")
    if ext and not basename.startswith("."):
        return ext

    # Dotfile mapping
    if basename in DOTFILE_MAP:
        return DOTFILE_MAP[basename]

    # Shebang detection
    try:
        with Path(filepath).open() as f:
            first_line = f.readline()
    except OSError:
        return None

    if first_line.startswith("#!"):
        for key, mapped_ext in SHEBANG_MAP.items():
            if key in first_line:
                return mapped_ext

    return None


def _load_allowlist(path: str = ".suppression-allowlist") -> list[str]:
    allowlist_path = Path(path)
    if not allowlist_path.is_file():
        return []

    patterns: list[str] = []
    for raw_line in allowlist_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _is_allowlisted(line_text: str, allowlist: list[str]) -> bool:
    for pattern in allowlist:
        try:
            if re.search(pattern, line_text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    """Entry point. Takes filenames as CLI args, returns 0 (clean) or 1 (violations)."""
    files = argv if argv is not None else sys.argv[1:]
    if not files:
        return 0

    allowlist = _load_allowlist()
    found_suppressions = False
    suppression_pattern_count = 0

    for filepath in files:
        if not Path(filepath).is_file():
            continue

        if _is_test_file(filepath):
            continue

        ext = _infer_extension(filepath)
        if ext is None:
            continue

        try:
            lines = Path(filepath).read_text().splitlines()
        except OSError:
            continue

        for regex, desc, extensions in SUPPRESSION_PATTERNS:
            if ext not in extensions:
                continue

            violation_lines: list[str] = []
            for lineno, line in enumerate(lines, 1):
                if re.search(regex, line, re.IGNORECASE):
                    match_text = f"{filepath}:{lineno}:{line}"
                    if not _is_allowlisted(match_text, allowlist):
                        violation_lines.append(f"{lineno}:{line}")
                    if len(violation_lines) >= _MAX_VIOLATIONS_PER_PATTERN:
                        break

            if violation_lines:
                found_suppressions = True
                suppression_pattern_count += 1
                print(f"{RED}ERROR: {desc} found in {filepath}{NC}")
                for vline in violation_lines:
                    print(f"  {YELLOW}{vline}{NC}")
                print()

    if found_suppressions:
        print(f"{RED}========================================{NC}")
        print(f"{RED}Found {suppression_pattern_count} suppression pattern(s) across files{NC}")
        print(f"{RED}========================================{NC}")
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
