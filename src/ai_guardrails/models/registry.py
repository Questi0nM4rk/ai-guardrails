"""ExceptionRegistry — domain model for .guardrails-exceptions.toml.

Represents approved suppressions, per-file ignores, and custom tool config
overrides. All data is typed via dataclasses; no raw dict[str, Any] exposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RuleException:
    """A single rule exception for a specific tool."""

    tool: str
    rule: str
    reason: str
    scope: str | None = None
    expires: str | None = None


@dataclass
class FileException:
    """A per-file glob exception for a tool."""

    glob: str
    tool: str
    rules: list[str]
    reason: str


@dataclass
class InlineSuppression:
    """An approved inline suppression pattern."""

    pattern: str
    reason: str


@dataclass
class ExceptionRegistry:
    """Parsed representation of .guardrails-exceptions.toml."""

    schema_version: int
    global_rules: dict[str, dict[str, Any]]
    exceptions: list[RuleException]
    file_exceptions: list[FileException]
    custom: dict[str, dict[str, Any]]
    inline_suppressions: list[InlineSuppression]

    @classmethod
    def from_toml(cls, data: dict[str, Any]) -> ExceptionRegistry:
        """Parse and validate a TOML-loaded dict into an ExceptionRegistry."""
        schema_version = data["schema_version"]

        exceptions = [
            RuleException(
                tool=exc["tool"],
                rule=exc["rule"],
                reason=exc["reason"],
                scope=exc.get("scope"),
                expires=exc.get("expires"),
            )
            for exc in data.get("exceptions", [])
        ]

        file_exceptions = [
            FileException(
                glob=fe["glob"],
                tool=fe["tool"],
                rules=list(fe["rules"]),
                reason=fe["reason"],
            )
            for fe in data.get("file_exceptions", [])
        ]

        inline_suppressions = [
            InlineSuppression(
                pattern=sup["pattern"],
                reason=sup["reason"],
            )
            for sup in data.get("inline_suppressions", [])
        ]

        return cls(
            schema_version=schema_version,
            global_rules=dict(data.get("global_rules", {})),
            exceptions=exceptions,
            file_exceptions=file_exceptions,
            custom=dict(data.get("custom", {})),
            inline_suppressions=inline_suppressions,
        )

    def get_ignores(self, tool: str) -> list[str]:
        """Return global rule ignores for a specific tool."""
        tool_config = self.global_rules.get(tool, {})
        return list(tool_config.get("ignore", []))

    def get_per_file_ignores(self, tool: str) -> dict[str, list[str]]:
        """Return per-file ignore mapping (glob -> rules) for a specific tool."""
        return {fe.glob: list(fe.rules) for fe in self.file_exceptions if fe.tool == tool}
