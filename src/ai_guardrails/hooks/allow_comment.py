"""Parse ai-guardrails-allow inline suppression comments."""

from __future__ import annotations

_PREFIXES = ("# ai-guardrails-allow:", "// ai-guardrails-allow:")


def parse_allow_comment(line: str) -> frozenset[str]:
    """Extract suppressed rule codes from an inline allow comment.

    Supports:
      # ai-guardrails-allow: UP007
      # ai-guardrails-allow: UP007,E501
      // ai-guardrails-allow: UP007
    Returns frozenset of rule code strings, empty if no allow comment.
    """
    stripped = line.strip()
    for prefix in _PREFIXES:
        idx = stripped.find(prefix)
        if idx != -1:
            after = stripped[idx + len(prefix) :]
            return frozenset(r.strip() for r in after.split(",") if r.strip())
    return frozenset()
