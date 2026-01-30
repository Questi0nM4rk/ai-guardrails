"""Test for README grammar and formatting rules."""

from __future__ import annotations

import re
from pathlib import Path


def test_readme_compound_modifiers_are_hyphenated() -> None:
    """Compound modifiers (adjectives before nouns) should be hyphenated."""
    readme_path = Path(__file__).parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    # Pattern: number + space + adjective + space + noun
    # These should be hyphenated: "120 char lines" -> "120-char lines"
    invalid_patterns = [
        r"\b\d+\s+char\s+lines\b",  # "100 char lines" should be "100-char lines"
        r"\b\d+\s+space\s+indent\b",  # "2 space indent" should be "2-space indent"
    ]

    errors = []
    for pattern in invalid_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            # Find line number for better error reporting
            lines_before = content[: match.start()].count("\n")
            errors.append(f"Line {lines_before + 1}: {match.group()} - should be hyphenated")

    assert not errors, "Compound modifier hyphenation issues:\n" + "\n".join(errors)
