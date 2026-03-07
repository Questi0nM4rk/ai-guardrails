"""Tests for PolicyLoader — org/team config hierarchy loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.infra.policy_loader import load_org_policy, load_team_policy

if TYPE_CHECKING:
    from pathlib import Path

_ORG_TOML = """\
default_profile = "standard"
allowed_profiles = ["standard", "strict"]

[locked_rules.ruff_S603]
rule = "ruff/S603"
reason = "All subprocess calls must use CommandRunner."
"""

_TEAM_TOML = """\
[team]
name = "platform"
owners = ["alice", "bob"]
profile = "strict"
exception_budget = 3
owns = ["src/platform/**"]

[locked_rules.ruff_ARG002]
rule = "ruff/ARG002"
reason = "Protocol stub args must be named."
"""


def test_load_org_policy_returns_none_when_file_missing(tmp_path: Path):
    result = load_org_policy(org_config_path=tmp_path / "nonexistent.toml")
    assert result is None


def test_load_org_policy_returns_policy_from_file(tmp_path: Path):
    config = tmp_path / "org.toml"
    config.write_text(_ORG_TOML)
    policy = load_org_policy(org_config_path=config)
    assert policy is not None
    assert policy.default_profile == "standard"
    assert "ruff_S603" in policy.locked_rules
    assert policy.locked_rules["ruff_S603"].rule == "ruff/S603"


def test_load_org_policy_allowed_profiles(tmp_path: Path):
    config = tmp_path / "org.toml"
    config.write_text(_ORG_TOML)
    policy = load_org_policy(org_config_path=config)
    assert policy is not None
    assert "standard" in policy.allowed_profiles
    assert "strict" in policy.allowed_profiles


def test_load_org_policy_is_locked(tmp_path: Path):
    config = tmp_path / "org.toml"
    config.write_text(_ORG_TOML)
    policy = load_org_policy(org_config_path=config)
    assert policy is not None
    assert policy.is_locked("ruff/S603")
    assert not policy.is_locked("ruff/E501")


def test_load_team_policy_returns_none_when_missing(tmp_path: Path):
    (tmp_path / "src").mkdir()
    result = load_team_policy(tmp_path / "src", git_root=tmp_path)
    assert result is None


def test_load_team_policy_found_in_project_dir(tmp_path: Path):
    (tmp_path / ".guardrails-team.toml").write_text(_TEAM_TOML)
    policy = load_team_policy(tmp_path, git_root=tmp_path)
    assert policy is not None
    assert policy.name == "platform"
    assert policy.exception_budget == 3
    assert "alice" in policy.owners


def test_load_team_policy_walks_up_to_parent(tmp_path: Path):
    """Team config in parent dir is found when searching from child dir."""
    child = tmp_path / "src" / "subpkg"
    child.mkdir(parents=True)
    (tmp_path / ".guardrails-team.toml").write_text(_TEAM_TOML)
    policy = load_team_policy(child, git_root=tmp_path)
    assert policy is not None
    assert policy.name == "platform"


def test_load_team_policy_uses_closest_config(tmp_path: Path):
    """Config in child dir takes precedence over parent."""
    child = tmp_path / "src"
    child.mkdir()
    (tmp_path / ".guardrails-team.toml").write_text('[team]\nname = "root"\n')
    child_team = '[team]\nname = "src-team"\nprofile = "strict"\n'
    (child / ".guardrails-team.toml").write_text(child_team)
    policy = load_team_policy(child, git_root=tmp_path)
    assert policy is not None
    assert policy.name == "src-team"


def test_load_team_policy_locked_rules(tmp_path: Path):
    (tmp_path / ".guardrails-team.toml").write_text(_TEAM_TOML)
    policy = load_team_policy(tmp_path, git_root=tmp_path)
    assert policy is not None
    assert "ruff_ARG002" in policy.locked_rules
