"""Tests for ProfileLoader — inheritance resolution, unknown profile, circular."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.infra.profile_loader import load_profile

_PROFILES_DIR = (
    Path(__file__).parent.parent.parent / "src" / "ai_guardrails" / "_data" / "profiles"
)


def test_load_standard_profile_returns_profile():
    profile = load_profile("standard", profiles_dir=_PROFILES_DIR)
    assert profile.name == "standard"
    assert profile.suppression_comments == "warn"
    assert profile.hold_the_line == "standard"
    assert profile.require_dual_approval is False


def test_load_minimal_profile_returns_minimal_values():
    profile = load_profile("minimal", profiles_dir=_PROFILES_DIR)
    assert profile.name == "minimal"
    assert profile.suppression_comments == "allow"
    assert profile.hold_the_line == "off"
    assert profile.exception_budget == 50


def test_load_strict_profile_returns_strict_values():
    profile = load_profile("strict", profiles_dir=_PROFILES_DIR)
    assert profile.name == "strict"
    assert profile.suppression_comments == "block"
    assert profile.hold_the_line == "strict"
    assert profile.require_dual_approval is True
    assert profile.exception_budget == 5


def test_strict_inherits_standard_as_base(tmp_path: Path):
    """strict.toml only overrides some fields — the rest come from standard."""
    strict = load_profile("strict", profiles_dir=_PROFILES_DIR)
    standard = load_profile("standard", profiles_dir=_PROFILES_DIR)
    # strict overrides these
    assert strict.suppression_comments == "block"
    assert strict.hold_the_line == "strict"
    assert strict.require_dual_approval is True
    # strict and standard agree on these (inherited, not overridden)
    assert strict.allow_syntax_require_expiry == standard.allow_syntax_require_expiry


def test_unknown_profile_raises_value_error():
    with pytest.raises(ValueError, match="Unknown profile 'bogus'"):
        load_profile("bogus", profiles_dir=_PROFILES_DIR)


def test_unknown_profile_lists_available_profiles():
    with pytest.raises(ValueError, match="standard"):
        load_profile("bogus", profiles_dir=_PROFILES_DIR)


def test_circular_inheritance_raises_value_error(tmp_path: Path):
    (tmp_path / "a.toml").write_text('name = "a"\ninherits = "b"\n')
    (tmp_path / "b.toml").write_text('name = "b"\ninherits = "a"\n')
    with pytest.raises(ValueError, match="Circular"):
        load_profile("a", profiles_dir=tmp_path)


def test_no_inheritance_loads_directly(tmp_path: Path):
    (tmp_path / "solo.toml").write_text(
        'name = "solo"\n'
        'suppression_comments = "allow"\n'
        "allow_syntax_require_expiry = false\n"
        "allow_syntax_require_ticket = false\n"
        "agent_commits_require_review = false\n"
        'hold_the_line = "off"\n'
        "exception_budget = 10\n"
        "require_dual_approval = false\n"
    )
    profile = load_profile("solo", profiles_dir=tmp_path)
    assert profile.name == "solo"
    assert profile.exception_budget == 10


def test_child_overrides_parent_field(tmp_path: Path):
    (tmp_path / "base.toml").write_text(
        'name = "base"\n'
        'suppression_comments = "allow"\n'
        "allow_syntax_require_expiry = false\n"
        "allow_syntax_require_ticket = false\n"
        "agent_commits_require_review = false\n"
        'hold_the_line = "off"\n'
        "exception_budget = 50\n"
        "require_dual_approval = false\n"
    )
    (tmp_path / "child.toml").write_text(
        'name = "child"\ninherits = "base"\nsuppression_comments = "block"\n'
    )
    profile = load_profile("child", profiles_dir=tmp_path)
    assert profile.suppression_comments == "block"
    assert profile.hold_the_line == "off"  # inherited from base
    assert profile.exception_budget == 50  # inherited from base
