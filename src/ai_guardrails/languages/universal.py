"""UniversalPlugin — always-active plugin absorbing the 4 tool-agnostic generators.

Generates:
- .editorconfig  (copy of base, hash-protected)
- .markdownlint.jsonc  (merged with registry ignores)
- .codespellrc  (generated from registry)
- .claude/settings.json  (deny rules + PreToolUse hook)

Hook config: base hooks always active regardless of language.
Generate and check helpers live in _universal_checks.py (200-line limit).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.languages._base import BaseLanguagePlugin
from ai_guardrails.languages._universal_checks import (
    check_claude_settings,
    check_codespellrc,
    check_editorconfig,
    check_markdownlint,
    generate_claude_settings,
    generate_codespellrc,
    generate_editorconfig,
    generate_markdownlint,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry


class UniversalPlugin(BaseLanguagePlugin):
    """Always-active plugin — generates universal configs for every project."""

    key = "universal"
    name = "Universal"
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = [
        ".editorconfig",
        ".markdownlint.jsonc",
        ".codespellrc",
        ".claude/settings.json",
    ]

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def detect(
        self,
        project_dir: Path,  # ai-guardrails-allow: ARG002 "always active"
    ) -> bool:
        """Always active — every project gets universal configs."""
        return True

    def generate(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> dict[Path, str]:
        """Generate all universal configs."""
        pairs = [
            generate_editorconfig(self._configs_dir, project_dir),
            generate_markdownlint(self._configs_dir, registry, project_dir),
            generate_codespellrc(registry, project_dir),
            generate_claude_settings(project_dir),
        ]
        return dict(pairs)

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return all stale/missing/tampered config descriptions."""
        issues: list[str] = []
        issues.extend(check_editorconfig(self._configs_dir, project_dir))
        issues.extend(check_markdownlint(self._configs_dir, registry, project_dir))
        issues.extend(check_codespellrc(registry, project_dir))
        issues.extend(check_claude_settings(project_dir))
        return issues
