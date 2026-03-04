"""Detect ignore-pattern edits in config files at commit time.

Pre-commit hook (defense in depth): catches ignore-pattern additions
in config files that slip past Claude Code hooks.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

from ai_guardrails.constants import CONFIG_PATTERN, IGNORE_PATTERN
from ai_guardrails.hooks._utils import has_hash_header


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def _staged_files() -> list[str]:
    output = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [f for f in output.splitlines() if f.strip()]


def _is_config_file(filename: str) -> bool:
    return bool(re.search(CONFIG_PATTERN, filename))


def _added_lines_for(filepath: str) -> list[str]:
    raw = _git("diff", "--cached", "-U0", filepath)
    return [
        line
        for line in raw.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _has_hash_header(filepath: str) -> bool:
    return has_hash_header(filepath)


def main() -> int:
    """Entry point. Returns 0 (clean) or 1 (violations found)."""
    staged = _staged_files()
    if not staged:
        return 0

    config_files = [f for f in staged if _is_config_file(f)]
    if not config_files:
        return 0

    found_violations = False

    for filepath in config_files:
        if not Path(filepath).is_file():
            continue

        if _has_hash_header(filepath):
            continue

        added = _added_lines_for(filepath)
        if not added:
            continue

        detected = [
            line for line in added if re.search(IGNORE_PATTERN, line, re.IGNORECASE)
        ]
        if detected:
            found_violations = True
            print(f"ERROR: Ignore pattern detected in {filepath}")
            print("Detected patterns:")
            for line in detected:
                print(f"  {line}")
            print()

    if found_violations:
        print("========================================")
        print("Direct ignore-pattern edits are not allowed")
        print("========================================")
        print()
        print("Lint exceptions must go in .guardrails-exceptions.toml,")
        print("not directly in config files.")
        print()
        print("Steps:")
        print("  1. Add the exception to .guardrails-exceptions.toml with a reason")
        print("  2. Run: ai-guardrails generate")
        print("  3. Commit the generated configs")
        print()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
