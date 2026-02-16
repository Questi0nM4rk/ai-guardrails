"""Unified exception registry: parse and validate .guardrails-exceptions.toml."""

from __future__ import annotations

import datetime
import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def _today() -> datetime.date:
    """Return today's date. Mockable for testing."""
    return datetime.datetime.now(tz=datetime.UTC).date()


def _ensure_list(val: str | list[str]) -> list[str]:
    """Normalize a string-or-list value to always be a list."""
    if isinstance(val, str):
        return [val]
    return list(val)


def _parse_date(val: object) -> datetime.date | None:
    """Parse a TOML date value to a Python date, or return None."""
    if val is None:
        return None
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        return datetime.date.fromisoformat(val)
    return None


@dataclass
class FileException:
    """A set of rules disabled for files matching a glob pattern."""

    glob: list[str]
    tool: str
    rules: list[str]
    reason: str
    expires: datetime.date | None = None


@dataclass
class InlineSuppression:
    """An approved inline suppression comment pattern."""

    pattern: str
    glob: list[str]
    reason: str
    expires: datetime.date | None = None


@dataclass
class ExceptionRegistry:
    """Parsed .guardrails-exceptions.toml content.

    Attributes:
        schema_version: Format version for forward compatibility.
        global_rules: Tool -> {rule_or_key: reason_or_value} mappings.
        file_exceptions: Per-file-pattern rule exceptions.
        inline_suppressions: Approved inline suppression patterns.
        skip: Tool -> [paths] for files excluded from scanning.

    """

    schema_version: int
    global_rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    file_exceptions: list[FileException] = field(default_factory=list)
    inline_suppressions: list[InlineSuppression] = field(default_factory=list)
    skip: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> ExceptionRegistry:
        """Load and parse a .guardrails-exceptions.toml file.

        Args:
            path: Path to the TOML file.

        Returns:
            Parsed ExceptionRegistry.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the TOML is invalid or missing schema_version.

        """
        if not path.exists():
            msg = f"Registry file not found: {path}"
            raise FileNotFoundError(msg)

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            msg = f"Failed to parse TOML: {e}"
            raise ValueError(msg) from e

        if "schema_version" not in data:
            msg = "Missing required field: schema_version"
            raise ValueError(msg)

        # Parse global rules
        global_section = data.get("global", {})
        global_rules: dict[str, dict[str, Any]] = {}
        for tool_name, tool_data in global_section.items():
            if isinstance(tool_data, dict):
                global_rules[tool_name] = dict(tool_data)

        # Parse file exceptions
        file_exceptions: list[FileException] = [
            FileException(
                glob=_ensure_list(fe_data.get("glob", [])),
                tool=fe_data.get("tool", ""),
                rules=fe_data.get("rules", []),
                reason=fe_data.get("reason", ""),
                expires=_parse_date(fe_data.get("expires")),
            )
            for fe_data in data.get("file_exceptions", [])
        ]

        # Parse inline suppressions
        inline_suppressions: list[InlineSuppression] = [
            InlineSuppression(
                pattern=sup_data.get("pattern", ""),
                glob=_ensure_list(sup_data.get("glob", [])),
                reason=sup_data.get("reason", ""),
                expires=_parse_date(sup_data.get("expires")),
            )
            for sup_data in data.get("inline_suppressions", [])
        ]

        # Parse skip patterns
        skip: dict[str, list[str]] = {
            tool_name: paths
            for tool_name, paths in data.get("skip", {}).items()
            if isinstance(paths, list)
        }

        return cls(
            schema_version=data["schema_version"],
            global_rules=global_rules,
            file_exceptions=file_exceptions,
            inline_suppressions=inline_suppressions,
            skip=skip,
        )

    def validate(self) -> list[str]:
        """Validate the registry for completeness.

        Returns:
            List of validation error strings. Empty means valid.

        """
        errors: list[str] = []

        # Check global ruff rules have non-empty reasons
        for tool, rules in self.global_rules.items():
            if tool in ("codespell", "pyright"):
                continue  # These use structured values, not string reasons
            for rule, reason in rules.items():
                if isinstance(reason, str) and not reason.strip():
                    errors.append(
                        f"global.{tool}.{rule}: empty reason",
                    )

        # Check file exceptions have reasons
        for i, fe in enumerate(self.file_exceptions):
            if not fe.reason:
                errors.append(
                    f"file_exceptions[{i}]: missing reason",
                )

        # Check inline suppressions have reasons
        for i, sup in enumerate(self.inline_suppressions):
            if not sup.reason:
                errors.append(
                    f"inline_suppressions[{i}]: missing reason",
                )

        # Check for expired exceptions
        today = _today()
        for i, fe in enumerate(self.file_exceptions):
            if fe.expires is not None and fe.expires < today:
                errors.append(
                    f"file_exceptions[{i}]: expired on {fe.expires}"
                    f" (glob={fe.glob}, tool={fe.tool})",
                )
        for i, sup in enumerate(self.inline_suppressions):
            if sup.expires is not None and sup.expires < today:
                errors.append(
                    f"inline_suppressions[{i}]: expired on {sup.expires} (pattern={sup.pattern})",
                )

        return errors

    def get_global_ignores(self, tool: str) -> list[str]:
        """Get the list of globally ignored rule codes for a tool.

        Args:
            tool: Tool name (e.g. "ruff", "markdownlint").

        Returns:
            List of rule codes.

        """
        rules = self.global_rules.get(tool, {})
        return [k for k, v in rules.items() if isinstance(v, str)]

    def get_file_exceptions(self, tool: str) -> list[FileException]:
        """Get file exceptions filtered by tool.

        Args:
            tool: Tool name (e.g. "ruff", "biome").

        Returns:
            List of FileException for that tool.

        """
        return [fe for fe in self.file_exceptions if fe.tool == tool]

    def get_expired(self) -> list[FileException | InlineSuppression]:
        """Return all exceptions that have passed their expiration date.

        Returns:
            List of expired FileException and InlineSuppression entries.

        """
        today = _today()
        expired: list[FileException | InlineSuppression] = [
            fe for fe in self.file_exceptions if fe.expires is not None and fe.expires < today
        ]
        expired.extend(
            sup
            for sup in self.inline_suppressions
            if sup.expires is not None and sup.expires < today
        )
        return expired
