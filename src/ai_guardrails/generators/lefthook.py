"""LefthookGenerator — tamper-protected lefthook.yml generation.

Generates a lefthook.yml with pre-commit hooks appropriate for the
detected languages. Always includes security hooks (gitleaks,
suppress-comments, validate-configs). Adds language-specific hooks
when the corresponding language is in the detected set.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import yaml

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    verify_hash,
)

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

# ---------------------------------------------------------------------------
# Hook definitions
# ---------------------------------------------------------------------------

_ALWAYS_HOOKS: dict[str, Any] = {
    "suppress-comments": {
        "glob": "*.{py,js,ts,tsx,jsx,rs,cs,go,lua,sh}",
        "run": (
            "uv run python -m ai_guardrails.hooks.suppress_comments {staged_files}"
        ),
        "priority": 2,
    },
    "protect-configs": {
        "glob": (
            "ruff.toml|biome.json|lefthook.yml|.editorconfig|.markdownlint.jsonc|.codespellrc"
        ),
        "run": ("uv run python -m ai_guardrails.hooks.protect_configs {staged_files}"),
        "priority": 2,
    },
    "gitleaks": {
        "run": "gitleaks protect --staged --no-banner",
        "priority": 2,
    },
    "detect-secrets": {
        "glob": "!.secrets.baseline",
        "run": "detect-secrets-hook --baseline .secrets.baseline {staged_files}",
        "priority": 2,
    },
    "codespell": {
        "glob": "*.{py,md,txt,yaml,yml,toml,json}",
        "run": "codespell --check-filenames {staged_files}",
        "priority": 2,
    },
    "markdownlint": {
        "glob": "*.md",
        "run": "markdownlint-cli2 {staged_files}",
        "priority": 2,
    },
    "validate-configs": {
        "run": "uv run python -m ai_guardrails generate --check",
        "priority": 2,
    },
}

_PYTHON_HOOKS: dict[str, Any] = {
    "python-format-and-stage": {
        "glob": "*.py",
        "run": (
            "uv run ruff format {staged_files}"
            " && uv run ruff check --fix {staged_files}"
            " && git add {staged_files}"
        ),
        "stage_fixed": True,
        "priority": 1,
    },
    "ruff-check": {
        "glob": "*.py",
        "run": "uv run ruff check {staged_files}",
        "priority": 2,
    },
}

_SHELL_HOOKS: dict[str, Any] = {
    "shell-format-and-stage": {
        "glob": "*.{sh,bash,zsh}",
        "run": "shfmt -i 2 -ci -bn -w {staged_files} && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "shellcheck": {
        "glob": "*.{sh,bash,zsh}",
        "run": "shellcheck --severity=info -x {staged_files}",
        "priority": 2,
    },
}

_COMMIT_MSG_HOOKS: dict[str, Any] = {
    "conventional": {
        "run": (
            r"grep -qE "
            r'"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)'
            r"(\\(.+\\))?!?:"
            r'" {1}'
        ),
    },
}


def _build_commands(languages: list[str]) -> dict[str, Any]:
    """Assemble pre-commit commands based on detected languages."""
    commands: dict[str, Any] = dict(_ALWAYS_HOOKS)
    if "python" in languages:
        commands.update(_PYTHON_HOOKS)
    if "shell" in languages:
        commands.update(_SHELL_HOOKS)
    return commands


class LefthookGenerator:
    """Generates tamper-protected lefthook.yml with language-appropriate hooks."""

    name = "lefthook"
    output_files: ClassVar[list[str]] = ["lefthook.yml"]

    def generate(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        languages: list[str],
        project_dir: Path,  # noqa: ARG002
    ) -> dict[Path, str]:
        """Return {Path("lefthook.yml"): content} with hash header."""
        body = self._build_body(languages)
        header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
        content = header + "\n" + body
        return {Path("lefthook.yml"): content}

    def check(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        project_dir: Path,
    ) -> list[str]:
        """Return stale/missing descriptions (empty list = fresh)."""
        target = project_dir / "lefthook.yml"
        if not target.exists():
            return ["lefthook.yml is missing — run: ai-guardrails generate"]
        existing = target.read_text(encoding="utf-8")
        # check() has no language list — detect staleness against no-language base
        body = self._build_body([])
        if not verify_hash(existing, body):
            return ["lefthook.yml is stale or tampered — run: ai-guardrails generate"]
        return []

    def _build_body(self, languages: list[str]) -> str:
        """Build the lefthook.yml body from language set."""
        config: dict[str, Any] = {
            "pre-commit": {"commands": _build_commands(languages)},
            "commit-msg": {"commands": _COMMIT_MSG_HOOKS},
        }
        return yaml.dump(config, default_flow_style=False, sort_keys=False)
