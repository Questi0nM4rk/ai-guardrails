"""Governance models: OrgPolicy, TeamPolicy, LockRule."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LockRule:
    """A rule that cannot be overridden at any lower governance level."""

    rule: str
    reason: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockRule:
        return cls(rule=data["rule"], reason=data["reason"])


@dataclass(frozen=True)
class OrgPolicy:
    """Organisation-level policy — top of the governance hierarchy."""

    locked_rules: dict[str, LockRule]
    default_profile: str
    allowed_profiles: tuple[str, ...]

    def is_locked(self, rule: str) -> bool:
        """Return True if the rule value is locked at org level."""
        return any(lr.rule == rule for lr in self.locked_rules.values())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrgPolicy:
        locked: dict[str, LockRule] = {
            key: LockRule.from_dict(val)
            for key, val in data.get("locked_rules", {}).items()
        }
        allowed = tuple(
            data.get("allowed_profiles", [data.get("default_profile", "standard")])
        )
        return cls(
            locked_rules=locked,
            default_profile=data.get("default_profile", "standard"),
            allowed_profiles=allowed,
        )


@dataclass(frozen=True)
class TeamPolicy:
    """Team-level policy — sits between org and project in the hierarchy."""

    name: str
    owners: tuple[str, ...]
    profile: str
    exception_budget: int | None
    owns: tuple[str, ...]
    locked_rules: dict[str, LockRule]
    overridable_rules: frozenset[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamPolicy:
        team = data.get("team", {})
        locked: dict[str, LockRule] = {
            key: LockRule.from_dict(val)
            for key, val in data.get("locked_rules", {}).items()
        }
        overridable = frozenset(data.get("overridable_rules", []))
        return cls(
            name=team.get("name", ""),
            owners=tuple(team.get("owners", [])),
            profile=team.get("profile", "standard"),
            exception_budget=team.get("exception_budget"),
            owns=tuple(team.get("owns", [])),
            locked_rules=locked,
            overridable_rules=overridable,
        )
