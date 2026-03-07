"""Tests for the ai-guardrails-allow inline suppression comment parser."""

from __future__ import annotations

from ai_guardrails.hooks.allow_comment import parse_allow_comment


def test_parse_allow_comment_python_single_rule() -> None:
    assert parse_allow_comment(
        "x: Optional[str]  # ai-guardrails-allow: UP007"
    ) == frozenset({"UP007"})


def test_parse_allow_comment_multiple_rules() -> None:
    assert parse_allow_comment("x = 1  # ai-guardrails-allow: UP007,E501") == frozenset(
        {"UP007", "E501"}
    )


def test_parse_allow_comment_cpp_style() -> None:
    assert parse_allow_comment(
        "auto x = foo();  // ai-guardrails-allow: UP007"
    ) == frozenset({"UP007"})


def test_parse_allow_comment_no_comment() -> None:
    assert parse_allow_comment("x: Optional[str]") == frozenset()


def test_parse_allow_comment_empty_string() -> None:
    assert parse_allow_comment("") == frozenset()


def test_parse_allow_comment_strips_whitespace() -> None:
    assert parse_allow_comment("x  # ai-guardrails-allow:  UP007 , E501 ") == frozenset(
        {"UP007", "E501"}
    )
