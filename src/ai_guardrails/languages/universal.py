"""UniversalPlugin — always-active plugin absorbing the 4 tool-agnostic generators.

Generates:
- .editorconfig  (copy of base, hash-protected)
- .markdownlint.jsonc  (merged with registry ignores)
- .codespellrc  (generated from registry)
- .claude/settings.json  (deny rules + PreToolUse hook)

Hook config: base hooks always active regardless of language.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ai_guardrails.constants import GENERATED_CONFIGS
from ai_guardrails.generators.base import (
    compute_hash,
    make_hash_header,
    verify_hash,
)
from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_JSONC_HASH_PREFIX = "// ai-guardrails:hash:sha256:"


def _strip_jsonc_comments(text: str) -> str:
    """Remove // line comments from JSONC content."""
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


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

    # ------------------------------------------------------------------
    # generate() helpers
    # ------------------------------------------------------------------

    def _generate_editorconfig(self, project_dir: Path) -> tuple[Path, str]:
        src = self._configs_dir / ".editorconfig"
        if not src.exists():
            raise FileNotFoundError(src)
        base = src.read_text()
        header = make_hash_header(base)
        return project_dir / ".editorconfig", f"{header}\n{base}"

    def _generate_markdownlint(
        self, registry: ExceptionRegistry, project_dir: Path
    ) -> tuple[Path, str]:
        src = self._configs_dir / ".markdownlint.jsonc"
        if not src.exists():
            raise FileNotFoundError(src)
        raw = src.read_text()
        config = json.loads(_strip_jsonc_comments(raw))
        for rule in registry.get_ignores("markdownlint"):
            config[rule] = False
        body = json.dumps(config, indent=2)
        header = f"{_JSONC_HASH_PREFIX}{compute_hash(body)}"
        return project_dir / ".markdownlint.jsonc", f"{header}\n{body}\n"

    def _generate_codespellrc(
        self, registry: ExceptionRegistry, project_dir: Path
    ) -> tuple[Path, str]:
        codespell_config = registry.global_rules.get("codespell", {})
        lines = ["[codespell]"]
        skip = codespell_config.get("skip", [])
        if skip:
            lines.append(f"skip = {','.join(skip)}")
        ignore_words = codespell_config.get("ignore_words", [])
        if ignore_words:
            lines.append(f"ignore-words-list = {','.join(ignore_words)}")
        lines.append("")
        body = "\n".join(lines)
        header = make_hash_header(body)
        return project_dir / ".codespellrc", f"{header}\n{body}"

    def _generate_claude_settings(self, project_dir: Path) -> tuple[Path, str]:
        edit_rules = [f"Edit({cfg})" for cfg in sorted(GENERATED_CONFIGS)]
        bash_rules = [
            "Bash(* --no-verify *)",
            "Bash(git commit * -n *)",
            "Bash(git push --force *)",
            "Bash(git push * --force *)",
        ]
        settings = {
            "permissions": {
                "deny": edit_rules + bash_rules,
            },
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python -m ai_guardrails.hooks.dangerous_cmd",
                            }
                        ],
                    }
                ]
            },
        }
        body = json.dumps(settings, indent=2)
        header = f"{_JSONC_HASH_PREFIX}{compute_hash(body)}"
        output_path = project_dir / ".claude" / "settings.json"
        return output_path, f"{header}\n{body}\n"

    def generate(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> dict[Path, str]:
        """Generate all universal configs."""
        outputs: dict[Path, str] = {}
        path, content = self._generate_editorconfig(project_dir)
        outputs[path] = content
        path, content = self._generate_markdownlint(registry, project_dir)
        outputs[path] = content
        path, content = self._generate_codespellrc(registry, project_dir)
        outputs[path] = content
        path, content = self._generate_claude_settings(project_dir)
        outputs[path] = content
        return outputs

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        """Return base hooks config — always merged into lefthook.yml."""
        return yaml.safe_load(self._HOOKS_YAML) or {}

    # ------------------------------------------------------------------
    # check() helpers
    # ------------------------------------------------------------------

    def _check_editorconfig(self, project_dir: Path) -> list[str]:
        target = project_dir / ".editorconfig"
        if not target.exists():
            return [".editorconfig is missing — run: ai-guardrails generate"]
        try:
            src = self._configs_dir / ".editorconfig"
            if not src.exists():
                return [".editorconfig base config not found in package data"]
            base = src.read_text()
        except OSError:
            return [".editorconfig base config not found in package data"]
        existing = target.read_text()
        if not verify_hash(existing, base):
            return [".editorconfig has been tampered with — run: ai-guardrails generate"]
        return []

    def _check_markdownlint(self, registry: ExceptionRegistry, project_dir: Path) -> list[str]:
        target = project_dir / ".markdownlint.jsonc"
        if not target.exists():
            return [".markdownlint.jsonc is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        try:
            src = self._configs_dir / ".markdownlint.jsonc"
            if not src.exists():
                return [".markdownlint.jsonc base config not found in package data"]
            raw = src.read_text()
            config = json.loads(_strip_jsonc_comments(raw))
            for rule in registry.get_ignores("markdownlint"):
                config[rule] = False
            expected_body = json.dumps(config, indent=2)
        except (OSError, json.JSONDecodeError):
            return [".markdownlint.jsonc base config not found in package data"]
        first_line = existing.split("\n", 1)[0].strip()
        if not first_line.startswith(_JSONC_HASH_PREFIX):
            return [".markdownlint.jsonc is stale or tampered — run: ai-guardrails generate"]
        stored_hash = first_line[len(_JSONC_HASH_PREFIX) :]
        if stored_hash != compute_hash(expected_body):
            return [".markdownlint.jsonc is stale or tampered — run: ai-guardrails generate"]
        return []

    def _check_codespellrc(self, registry: ExceptionRegistry, project_dir: Path) -> list[str]:
        target = project_dir / ".codespellrc"
        if not target.exists():
            return [".codespellrc is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        codespell_config = registry.global_rules.get("codespell", {})
        lines = ["[codespell]"]
        skip = codespell_config.get("skip", [])
        if skip:
            lines.append(f"skip = {','.join(skip)}")
        ignore_words = codespell_config.get("ignore_words", [])
        if ignore_words:
            lines.append(f"ignore-words-list = {','.join(ignore_words)}")
        lines.append("")
        expected_body = "\n".join(lines)
        if not verify_hash(existing, expected_body):
            return [".codespellrc is stale or tampered — run: ai-guardrails generate"]
        return []

    def _check_claude_settings(self, project_dir: Path) -> list[str]:
        target = project_dir / ".claude" / "settings.json"
        if not target.exists():
            return [".claude/settings.json is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        first_line = existing.split("\n", 1)[0].strip()
        if not first_line.startswith(_JSONC_HASH_PREFIX):
            return [".claude/settings.json is stale or tampered — run: ai-guardrails generate"]
        stored_hash = first_line[len(_JSONC_HASH_PREFIX) :]
        edit_rules = [f"Edit({cfg})" for cfg in sorted(GENERATED_CONFIGS)]
        bash_rules = [
            "Bash(* --no-verify *)",
            "Bash(git commit * -n *)",
            "Bash(git push --force *)",
            "Bash(git push * --force *)",
        ]
        settings = {
            "permissions": {"deny": edit_rules + bash_rules},
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python -m ai_guardrails.hooks.dangerous_cmd",
                            }
                        ],
                    }
                ]
            },
        }
        expected_body = json.dumps(settings, indent=2)
        if stored_hash != compute_hash(expected_body):
            return [".claude/settings.json is stale or tampered — run: ai-guardrails generate"]
        return []

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return all stale/missing/tampered config descriptions."""
        issues: list[str] = []
        issues.extend(self._check_editorconfig(project_dir))
        issues.extend(self._check_markdownlint(registry, project_dir))
        issues.extend(self._check_codespellrc(registry, project_dir))
        issues.extend(self._check_claude_settings(project_dir))
        return issues
