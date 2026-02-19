"""Tests for review thread resolution category enforcement.

Every resolve message must start with a valid category prefix:
- 'Fixed in <commit-hash>'
- 'False positive: <reason>'
- 'Won't fix: <reason>'

Resolving without a valid category should be rejected.
"""

from __future__ import annotations

from guardrails.comments import VALID_RESOLVE_CATEGORIES, validate_resolve_message

# ---------------------------------------------------------------------------
# validate_resolve_message — valid messages
# ---------------------------------------------------------------------------


def test_validate_fixed_in_message() -> None:
    """Messages starting with 'Fixed in' should be accepted."""
    assert validate_resolve_message("Fixed in abc1234") is True


def test_validate_fixed_in_case_insensitive() -> None:
    """Category matching should be case-insensitive."""
    assert validate_resolve_message("fixed in abc1234") is True


def test_validate_false_positive_message() -> None:
    """Messages starting with 'False positive:' should be accepted."""
    assert validate_resolve_message("False positive: this rule doesn't apply here") is True


def test_validate_wont_fix_message() -> None:
    r"""Messages starting with \"Won't fix:\" should be accepted."""
    assert validate_resolve_message("Won't fix: intentional design decision") is True


def test_validate_wont_fix_curly_apostrophe() -> None:
    """Won't fix with curly apostrophe should also be accepted."""
    assert validate_resolve_message("Won\u2019t fix: intentional") is True


# ---------------------------------------------------------------------------
# validate_resolve_message — invalid messages
# ---------------------------------------------------------------------------


def test_validate_rejects_acknowledged() -> None:
    """'Acknowledged' is not a valid resolution category."""
    assert validate_resolve_message("Acknowledged") is False


def test_validate_rejects_noted() -> None:
    """'Noted' is not a valid resolution category."""
    assert validate_resolve_message("Noted") is False


def test_validate_rejects_empty_string() -> None:
    """Empty string is not a valid resolve message."""
    assert validate_resolve_message("") is False


def test_validate_rejects_arbitrary_text() -> None:
    """Arbitrary text without a valid category prefix is rejected."""
    assert validate_resolve_message("I looked at this and it seems fine") is False


def test_validate_rejects_none() -> None:
    """None (no message) is not valid for resolve."""
    assert validate_resolve_message(None) is False


def test_validate_rejects_whitespace_only() -> None:
    """Whitespace-only string is not a valid resolve message."""
    assert validate_resolve_message("   ") is False


# ---------------------------------------------------------------------------
# validate_resolve_message — edge cases
# ---------------------------------------------------------------------------


def test_validate_fixed_in_with_extra_whitespace() -> None:
    """Leading/trailing whitespace around a valid message should still pass."""
    assert validate_resolve_message("  Fixed in abc1234  ") is True


def test_validate_false_positive_without_explanation_fails() -> None:
    """'False positive:' without explanation should be rejected."""
    assert validate_resolve_message("False positive:") is False


def test_validate_wont_fix_without_explanation_fails() -> None:
    r"""\"Won't fix:\" without explanation should be rejected."""
    assert validate_resolve_message("Won't fix:") is False


def test_validate_fixed_in_without_hash_fails() -> None:
    """'Fixed in' without a commit hash should be rejected."""
    assert validate_resolve_message("Fixed in") is False


# ---------------------------------------------------------------------------
# VALID_RESOLVE_CATEGORIES constant
# ---------------------------------------------------------------------------


def test_valid_categories_is_tuple() -> None:
    """VALID_RESOLVE_CATEGORIES should be an immutable sequence."""
    assert isinstance(VALID_RESOLVE_CATEGORIES, tuple)


def test_valid_categories_contains_expected() -> None:
    """All three expected categories should be present."""
    lower_cats = [c.lower() for c in VALID_RESOLVE_CATEGORIES]
    assert "fixed in" in lower_cats
    assert "false positive:" in lower_cats
    assert "won't fix:" in lower_cats
