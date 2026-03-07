"""Profile model — enforcement posture configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Profile:
    """Enforcement posture for a team or project."""

    name: str
    suppression_comments: Literal["block", "warn", "allow"]
    allow_syntax_require_expiry: bool
    allow_syntax_require_ticket: bool
    agent_commits_require_review: bool
    hold_the_line: Literal["strict", "standard", "off"]
    exception_budget: int | None  # None = unlimited
    require_dual_approval: bool
    inherits: str | None  # profile name to inherit from

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        return cls(
            name=data["name"],
            suppression_comments=data.get("suppression_comments", "block"),
            allow_syntax_require_expiry=data.get("allow_syntax_require_expiry", False),
            allow_syntax_require_ticket=data.get("allow_syntax_require_ticket", False),
            agent_commits_require_review=data.get(
                "agent_commits_require_review", False
            ),
            hold_the_line=data.get("hold_the_line", "standard"),
            exception_budget=data.get("exception_budget"),
            require_dual_approval=data.get("require_dual_approval", False),
            inherits=data.get("inherits"),
        )
