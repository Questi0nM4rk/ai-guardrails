"""Parse ai-guardrails-allow inline suppression comments.

Valid format:
  # ai-guardrails-allow: RULE "reason text"
  # ai-guardrails-allow: RULE1, RULE2 "reason text"
  // ai-guardrails-allow: RULE "reason text"

A quoted reason is mandatory. Allow comments without a reason are invalid
suppressions and will be reported as AI001 by `ai-guardrails check`.
"""

from __future__ import annotations

_PREFIXES = ("# ai-guardrails-allow:", "// ai-guardrails-allow:")


def parse_allow_comment(line: str) -> frozenset[str]:
    """Extract rule codes from a *valid* allow comment (reason required).

    Returns frozenset of rule codes when the comment includes a quoted reason.
    Returns empty frozenset if no allow comment OR if the reason is missing.
    """
    stripped = line.strip()
    for prefix in _PREFIXES:
        idx = stripped.find(prefix)
        if idx != -1:
            after = stripped[idx + len(prefix) :]
            if '"' not in after:
                return frozenset()  # bare allow (no reason) — not a valid suppression
            rules_part = after[: after.index('"')].strip()
            return frozenset(r.strip() for r in rules_part.split(",") if r.strip())
    return frozenset()


def get_bare_allowed_rules(line: str) -> frozenset[str]:
    """Return rule codes from allow comments that are *missing* a reason.

    These are invalid suppressions. `check_step` uses this to emit AI001.
    Returns empty frozenset when the comment is valid or absent.
    """
    stripped = line.strip()
    for prefix in _PREFIXES:
        idx = stripped.find(prefix)
        if idx != -1:
            after = stripped[idx + len(prefix) :]
            if '"' in after:
                return frozenset()  # has reason → valid, not bare
            return frozenset(r.strip() for r in after.split(",") if r.strip())
    return frozenset()
