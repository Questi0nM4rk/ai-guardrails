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
            "ruff.toml|lefthook.yml|.editorconfig|.markdownlint.jsonc|.codespellrc"
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
            " && uv run ruff check --fix --exit-zero {staged_files}"
            " && git add {staged_files}"
        ),
        "stage_fixed": True,
        "priority": 1,
    },
    "guardrails-check": {
        "glob": "*.py",
        "run": "uv run python -m ai_guardrails check",
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

_CPP_HOOKS: dict[str, Any] = {
    "clang-format-and-stage": {
        "glob": "*.{c,h,cpp,hpp,cc,cxx,hxx}",
        "run": "clang-format -i {staged_files} && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "clang-tidy": {
        "glob": "*.{c,h,cpp,hpp,cc,cxx,hxx}",
        "run": "clang-tidy {staged_files} -- -Wall -Wextra",
        "priority": 2,
    },
}

_DOTNET_HOOKS: dict[str, Any] = {
    "dotnet-format-and-stage": {
        "glob": "*.{cs,csx,vb}",
        "run": "dotnet format --severity info && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "dotnet-build": {
        "glob": "*.{cs,csx,vb,csproj,sln}",
        "run": "dotnet build --no-restore -warnaserror -c Release",
        "priority": 2,
    },
}

_GO_HOOKS: dict[str, Any] = {
    "go-format-and-stage": {
        "glob": "*.go",
        "run": "gofmt -w {staged_files} && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "go-vet": {
        "glob": "*.go",
        "run": "go vet ./...",
        "priority": 2,
    },
    "staticcheck": {
        "glob": "*.go",
        "run": "staticcheck ./...",
        "priority": 2,
    },
}

_LUA_HOOKS: dict[str, Any] = {
    "lua-format-and-stage": {
        "glob": "*.lua",
        "run": "stylua {staged_files} && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "luacheck": {
        "glob": "*.lua",
        "run": "luacheck {staged_files}",
        "priority": 2,
    },
}

_NODE_HOOKS: dict[str, Any] = {
    "node-format-and-stage": {
        "glob": "*.{js,jsx,ts,tsx,mjs,cjs}",
        "run": "biome check --apply {staged_files} && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "biome-check": {
        "glob": "*.{js,jsx,ts,tsx,mjs,cjs}",
        "run": "biome check --error-on-warnings {staged_files}",
        "priority": 2,
    },
}

_RUST_HOOKS: dict[str, Any] = {
    "rust-format-and-stage": {
        "glob": "*.rs",
        "run": "cargo fmt --all && git add {staged_files}",
        "stage_fixed": True,
        "priority": 1,
    },
    "cargo-clippy": {
        "glob": "*.rs",
        "run": (
            "cargo clippy --all-targets --all-features --"
            " -D warnings -D clippy::pedantic -D clippy::nursery"
            " -A clippy::module_name_repetitions"
        ),
        "priority": 2,
    },
    "cargo-audit": {
        "run": "cargo audit --deny warnings",
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

_LANGUAGE_HOOKS: dict[str, dict[str, Any]] = {
    "python": _PYTHON_HOOKS,
    "shell": _SHELL_HOOKS,
    "cpp": _CPP_HOOKS,
    "dotnet": _DOTNET_HOOKS,
    "go": _GO_HOOKS,
    "lua": _LUA_HOOKS,
    "node": _NODE_HOOKS,
    "rust": _RUST_HOOKS,
}


def _build_commands(languages: list[str]) -> dict[str, Any]:
    """Assemble pre-commit commands based on detected languages."""
    commands: dict[str, Any] = dict(_ALWAYS_HOOKS)
    for lang in languages:
        if lang in _LANGUAGE_HOOKS:
            commands.update(_LANGUAGE_HOOKS[lang])
    return commands


class LefthookGenerator:
    """Generates tamper-protected lefthook.yml with language-appropriate hooks."""

    name = "lefthook"
    output_files: ClassVar[list[str]] = ["lefthook.yml"]

    def generate(
        self,
        registry: ExceptionRegistry,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
        languages: list[str],
        project_dir: Path,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
    ) -> dict[Path, str]:
        """Return {Path("lefthook.yml"): content} with hash header."""
        body = self._build_body(languages)
        header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
        content = header + "\n" + body
        return {Path("lefthook.yml"): content}

    def check(
        self,
        registry: ExceptionRegistry,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
        project_dir: Path,
        languages: list[str] | None = None,
    ) -> list[str]:
        """Return stale/missing descriptions (empty list = fresh)."""
        target = project_dir / "lefthook.yml"
        if not target.exists():
            return ["lefthook.yml is missing — run: ai-guardrails generate"]
        existing = target.read_text(encoding="utf-8")
        body = self._build_body(languages or [])
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
