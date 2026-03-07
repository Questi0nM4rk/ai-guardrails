"""Tests for the ai-guardrails-allow inline suppression comment parser."""

from __future__ import annotations

from ai_guardrails.hooks.allow_comment import (
    get_bare_allowed_rules,
    parse_allow_comment,
)

# ---------------------------------------------------------------------------
# parse_allow_comment — requires a quoted reason; empty when bare/absent
# ---------------------------------------------------------------------------


def test_parse_allow_comment_with_reason_returns_rules() -> None:
    assert parse_allow_comment(
        'x: Optional[str]  # ai-guardrails-allow: UP007 "use X | Y instead"'
    ) == frozenset({"UP007"})


def test_parse_allow_comment_multiple_rules_with_reason() -> None:
    assert parse_allow_comment(
        'x = 1  # ai-guardrails-allow: UP007, E501 "legacy line"'
    ) == frozenset({"UP007", "E501"})


def test_parse_allow_comment_cpp_style_with_reason() -> None:
    assert parse_allow_comment(
        'auto x = foo();  // ai-guardrails-allow: UP007 "C++ legacy"'
    ) == frozenset({"UP007"})


def test_parse_allow_comment_bare_returns_empty() -> None:
    """Bare allow comment (no reason) must NOT suppress — returns empty."""
    assert (
        parse_allow_comment("x: Optional[str]  # ai-guardrails-allow: UP007")
        == frozenset()
    )


def test_parse_allow_comment_no_comment() -> None:
    assert parse_allow_comment("x: Optional[str]") == frozenset()


def test_parse_allow_comment_empty_string() -> None:
    assert parse_allow_comment("") == frozenset()


def test_parse_allow_comment_strips_whitespace_around_rules() -> None:
    assert parse_allow_comment(
        'x  # ai-guardrails-allow:  UP007 , E501 "reason"'
    ) == frozenset({"UP007", "E501"})


# ---------------------------------------------------------------------------
# get_bare_allowed_rules — returns rules from comments that are missing reason
# ---------------------------------------------------------------------------


def test_get_bare_allowed_rules_bare_single_rule() -> None:
    assert get_bare_allowed_rules("x  # ai-guardrails-allow: UP007") == frozenset(
        {"UP007"}
    )


def test_get_bare_allowed_rules_bare_multiple_rules() -> None:
    assert get_bare_allowed_rules("x  # ai-guardrails-allow: UP007, E501") == frozenset(
        {"UP007", "E501"}
    )


def test_get_bare_allowed_rules_valid_comment_returns_empty() -> None:
    """A valid (with reason) allow comment is NOT bare."""
    assert (
        get_bare_allowed_rules('x  # ai-guardrails-allow: UP007 "reason"')
        == frozenset()
    )


def test_get_bare_allowed_rules_no_comment_returns_empty() -> None:
    assert get_bare_allowed_rules("x = 1") == frozenset()
