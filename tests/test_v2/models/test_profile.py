"""Tests for Profile model — enforcement posture fields."""

from __future__ import annotations

import pytest

from ai_guardrails.models.profile import Profile


def test_strict_profile_fields():
    profile = Profile(
        name="strict",
        suppression_comments="block",
        allow_syntax_require_expiry=True,
        allow_syntax_require_ticket=True,
        agent_commits_require_review=True,
        hold_the_line="strict",
        exception_budget=0,
        require_dual_approval=True,
        inherits=None,
    )
    assert profile.name == "strict"
    assert profile.suppression_comments == "block"
    assert profile.allow_syntax_require_expiry is True
    assert profile.allow_syntax_require_ticket is True
    assert profile.agent_commits_require_review is True
    assert profile.hold_the_line == "strict"
    assert profile.exception_budget == 0
    assert profile.require_dual_approval is True
    assert profile.inherits is None


def test_standard_profile_fields():
    profile = Profile(
        name="standard",
        suppression_comments="block",
        allow_syntax_require_expiry=True,
        allow_syntax_require_ticket=False,
        agent_commits_require_review=False,
        hold_the_line="standard",
        exception_budget=20,
        require_dual_approval=False,
        inherits=None,
    )
    assert profile.exception_budget == 20
    assert profile.allow_syntax_require_ticket is False
    assert profile.hold_the_line == "standard"


def test_minimal_profile_fields():
    profile = Profile(
        name="minimal",
        suppression_comments="warn",
        allow_syntax_require_expiry=False,
        allow_syntax_require_ticket=False,
        agent_commits_require_review=False,
        hold_the_line="off",
        exception_budget=None,
        require_dual_approval=False,
        inherits=None,
    )
    assert profile.suppression_comments == "warn"
    assert profile.hold_the_line == "off"
    assert profile.exception_budget is None


def test_profile_is_frozen():
    profile = Profile(
        name="strict",
        suppression_comments="block",
        allow_syntax_require_expiry=True,
        allow_syntax_require_ticket=True,
        agent_commits_require_review=True,
        hold_the_line="strict",
        exception_budget=0,
        require_dual_approval=True,
        inherits=None,
    )
    with pytest.raises(AttributeError):
        profile.name = "minimal"  # type: ignore[misc]


def test_profile_with_inheritance():
    profile = Profile(
        name="fintech-strict",
        suppression_comments="block",
        allow_syntax_require_expiry=True,
        allow_syntax_require_ticket=True,
        agent_commits_require_review=True,
        hold_the_line="strict",
        exception_budget=0,
        require_dual_approval=True,
        inherits="strict",
    )
    assert profile.inherits == "strict"


def test_profile_unlimited_budget_none():
    profile = Profile(
        name="minimal",
        suppression_comments="allow",
        allow_syntax_require_expiry=False,
        allow_syntax_require_ticket=False,
        agent_commits_require_review=False,
        hold_the_line="off",
        exception_budget=None,
        require_dual_approval=False,
        inherits=None,
    )
    assert profile.exception_budget is None


def test_profile_from_dict():
    data = {
        "name": "standard",
        "suppression_comments": "block",
        "allow_syntax_require_expiry": True,
        "allow_syntax_require_ticket": False,
        "agent_commits_require_review": False,
        "hold_the_line": "standard",
        "exception_budget": 20,
        "require_dual_approval": False,
        "inherits": None,
    }
    profile = Profile.from_dict(data)
    assert profile.name == "standard"
    assert profile.exception_budget == 20
    assert profile.hold_the_line == "standard"


def test_profile_from_dict_optional_fields_default():
    """Fields with sensible defaults when omitted."""
    data = {
        "name": "custom",
        "suppression_comments": "block",
        "hold_the_line": "standard",
    }
    profile = Profile.from_dict(data)
    assert profile.name == "custom"
    assert profile.allow_syntax_require_expiry is False
    assert profile.allow_syntax_require_ticket is False
    assert profile.agent_commits_require_review is False
    assert profile.exception_budget is None
    assert profile.require_dual_approval is False
    assert profile.inherits is None


def test_profile_suppression_comments_values():
    for val in ("block", "warn", "allow"):
        p = Profile(
            name="test",
            suppression_comments=val,  # type: ignore[arg-type]
            allow_syntax_require_expiry=False,
            allow_syntax_require_ticket=False,
            agent_commits_require_review=False,
            hold_the_line="off",
            exception_budget=None,
            require_dual_approval=False,
            inherits=None,
        )
        assert p.suppression_comments == val


def test_profile_hold_the_line_values():
    for val in ("strict", "standard", "off"):
        p = Profile(
            name="test",
            suppression_comments="block",
            allow_syntax_require_expiry=False,
            allow_syntax_require_ticket=False,
            agent_commits_require_review=False,
            hold_the_line=val,  # type: ignore[arg-type]
            exception_budget=None,
            require_dual_approval=False,
            inherits=None,
        )
        assert p.hold_the_line == val
