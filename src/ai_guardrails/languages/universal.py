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

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

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
    from ai_guardrails.models.registry import ExceptionRegistry


class UniversalPlugin(BaseLanguagePlugin):
    """Always-active plugin — generates universal configs for every project."""

    key = "universal"
    name = "Universal"
    copy_files: list[str] = []
    generated_configs = [
        ".editorconfig",
        ".markdownlint.jsonc",
        ".codespellrc",
        ".claude/settings.json",
    ]

    # Base hooks — content from templates/lefthook/base.yaml, embedded here
    _HOOKS_YAML = """\
pre-commit:
  commands:
    suppress-comments:
      glob: "*.{py,js,ts,tsx,jsx,rs,cs,go,lua,sh}"
      run: python -m ai_guardrails.hooks.suppress_comments {staged_files}
      priority: 2
    protect-configs:
      glob: "ruff.toml|biome.json|lefthook.yml|.editorconfig|.markdownlint.jsonc|.codespellrc"
      run: python -m ai_guardrails.hooks.protect_configs {staged_files}
      priority: 2
    gitleaks:
      run: gitleaks detect --staged --no-banner
      priority: 2
    detect-secrets:
      glob: "!.secrets.baseline"
      run: detect-secrets-hook --baseline .secrets.baseline {staged_files}
      priority: 2
    codespell:
      glob: "*.{py,md,txt,yaml,yml,toml,json}"
      run: codespell --check-filenames {staged_files}
      priority: 2
    markdownlint:
      glob: "*.md"
      run: markdownlint-cli2 {staged_files}
      priority: 2
    validate-configs:
      run: python -m ai_guardrails generate --check
      priority: 2
commit-msg:
  commands:
    conventional:
      run: >-
        echo "{1}" | grep -qE
        "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\\(.+\\))?!?:"
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def detect(self, project_dir: Path) -> bool:
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

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        """Return base hooks config — always merged into lefthook.yml."""
        return yaml.safe_load(self._HOOKS_YAML) or {}

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
