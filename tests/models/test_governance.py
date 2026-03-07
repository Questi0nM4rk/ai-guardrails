"""Tests for governance models: OrgPolicy, TeamPolicy, LockRule."""

from __future__ import annotations

import pytest

from ai_guardrails.models.governance import LockRule, OrgPolicy, TeamPolicy


def test_lock_rule_instantiation():
    rule = LockRule(rule="ruff/S603", reason="no subprocess in production")
    assert rule.rule == "ruff/S603"
    assert rule.reason == "no subprocess in production"


def test_lock_rule_is_frozen():
    rule = LockRule(rule="gitleaks", reason="secrets scanning non-negotiable")
    with pytest.raises(AttributeError):
        rule.reason = "changed"  # type: ignore[misc]


def test_org_policy_instantiation():
    policy = OrgPolicy(
        locked_rules={
            "gitleaks": LockRule(
                rule="gitleaks", reason="secrets scanning non-negotiable"
            ),
            "ruff/S603": LockRule(
                rule="ruff/S603", reason="no subprocess in production"
            ),
        },
        default_profile="standard",
        allowed_profiles=("strict", "standard"),
    )
    assert "gitleaks" in policy.locked_rules
    assert policy.default_profile == "standard"
    assert "strict" in policy.allowed_profiles


def test_org_policy_is_frozen():
    policy = OrgPolicy(
        locked_rules={}, default_profile="standard", allowed_profiles=("strict",)
    )
    with pytest.raises(AttributeError):
        policy.default_profile = "minimal"  # type: ignore[misc]


def test_org_policy_empty_locked_rules():
    policy = OrgPolicy(
        locked_rules={}, default_profile="minimal", allowed_profiles=("minimal",)
    )
    assert policy.locked_rules == {}


def test_team_policy_instantiation():
    policy = TeamPolicy(
        name="backend",
        owners=("alice", "bob"),
        profile="strict",
        exception_budget=10,
        owns=("src/api/", "src/models/"),
        locked_rules={
            "ruff/ARG002": LockRule(
                rule="ruff/ARG002", reason="Protocol pattern required in all services"
            )
        },
        overridable_rules=frozenset({"ruff/E501"}),
    )
    assert policy.name == "backend"
    assert "alice" in policy.owners
    assert policy.profile == "strict"
    assert policy.exception_budget == 10
    assert "src/api/" in policy.owns
    assert "ruff/ARG002" in policy.locked_rules
    assert "ruff/E501" in policy.overridable_rules


def test_team_policy_is_frozen():
    policy = TeamPolicy(
        name="frontend",
        owners=("carol",),
        profile="standard",
        exception_budget=20,
        owns=("src/ui/",),
        locked_rules={},
        overridable_rules=frozenset(),
    )
    with pytest.raises(AttributeError):
        policy.name = "backend"  # type: ignore[misc]


def test_team_policy_unlimited_budget():
    policy = TeamPolicy(
        name="infra",
        owners=(),
        profile="minimal",
        exception_budget=None,
        owns=(),
        locked_rules={},
        overridable_rules=frozenset(),
    )
    assert policy.exception_budget is None


def test_org_policy_from_dict():
    data = {
        "locked_rules": {
            "gitleaks": {
                "rule": "gitleaks",
                "reason": "secrets scanning non-negotiable",
            },
        },
        "default_profile": "standard",
        "allowed_profiles": ["strict", "standard"],
    }
    policy = OrgPolicy.from_dict(data)
    assert "gitleaks" in policy.locked_rules
    assert policy.locked_rules["gitleaks"].reason == "secrets scanning non-negotiable"
    assert policy.default_profile == "standard"
    assert "strict" in policy.allowed_profiles


def test_team_policy_from_dict():
    data = {
        "team": {
            "name": "backend",
            "owners": ["alice", "bob"],
            "profile": "strict",
            "exception_budget": 10,
            "owns": ["src/api/"],
        },
        "locked_rules": {
            "ruff/ARG002": {
                "rule": "ruff/ARG002",
                "reason": "Protocol pattern required",
            },
        },
        "overridable_rules": ["ruff/E501"],
    }
    policy = TeamPolicy.from_dict(data)
    assert policy.name == "backend"
    assert "alice" in policy.owners
    assert "ruff/ARG002" in policy.locked_rules
    assert "ruff/E501" in policy.overridable_rules


def test_lock_rule_is_locked_for_rule():
    org = OrgPolicy(
        locked_rules={"gitleaks": LockRule(rule="gitleaks", reason="non-negotiable")},
        default_profile="standard",
        allowed_profiles=("standard",),
    )
    assert org.is_locked("gitleaks")
    assert not org.is_locked("ruff/E501")
