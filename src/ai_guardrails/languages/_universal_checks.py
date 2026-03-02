"""Generate and check helpers for UniversalPlugin.

Extracted to keep universal.py under the 200-line module limit.
Each function either builds or verifies one generated config file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.constants import GENERATED_CONFIGS
from ai_guardrails.generators.base import compute_hash, make_hash_header, verify_hash

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_JSONC_HASH_PREFIX = "// ai-guardrails:hash:sha256:"


def strip_jsonc_comments(text: str) -> str:
    """Remove // line comments from JSONC content."""
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def generate_editorconfig(configs_dir: Path, project_dir: Path) -> tuple[Path, str]:
    """Return (path, content) for .editorconfig with hash header."""
    src = configs_dir / ".editorconfig"
    if not src.exists():
        raise FileNotFoundError(src)
    base = src.read_text()
    header = make_hash_header(base)
    return project_dir / ".editorconfig", f"{header}\n{base}"


def generate_markdownlint(
    configs_dir: Path, registry: ExceptionRegistry, project_dir: Path
) -> tuple[Path, str]:
    """Return (path, content) for .markdownlint.jsonc merged with registry."""
    src = configs_dir / ".markdownlint.jsonc"
    if not src.exists():
        raise FileNotFoundError(src)
    raw = src.read_text()
    config = json.loads(strip_jsonc_comments(raw))
    for rule in registry.get_ignores("markdownlint"):
        config[rule] = False
    body = json.dumps(config, indent=2)
    header = f"{_JSONC_HASH_PREFIX}{compute_hash(body)}"
    return project_dir / ".markdownlint.jsonc", f"{header}\n{body}\n"


def generate_codespellrc(registry: ExceptionRegistry, project_dir: Path) -> tuple[Path, str]:
    """Return (path, content) for .codespellrc from registry."""
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


def generate_claude_settings(project_dir: Path) -> tuple[Path, str]:
    """Return (path, content) for .claude/settings.json with deny rules."""
    edit_rules = [f"Edit({cfg})" for cfg in sorted(GENERATED_CONFIGS)]
    bash_rules = [
        "Bash(* --no-verify *)",
        "Bash(git commit * -n *)",
        "Bash(git push --force *)",
        "Bash(git push * --force *)",
    ]
    pre_tool_hook = {"type": "command", "command": "python -m ai_guardrails.hooks.dangerous_cmd"}
    settings = {
        "permissions": {"deny": edit_rules + bash_rules},
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [pre_tool_hook]}]},
    }
    body = json.dumps(settings, indent=2)
    header = f"{_JSONC_HASH_PREFIX}{compute_hash(body)}"
    return project_dir / ".claude" / "settings.json", f"{header}\n{body}\n"


def check_editorconfig(configs_dir: Path, project_dir: Path) -> list[str]:
    """Return issues if .editorconfig is missing or tampered."""
    target = project_dir / ".editorconfig"
    if not target.exists():
        return [".editorconfig is missing — run: ai-guardrails generate"]
    try:
        src = configs_dir / ".editorconfig"
        if not src.exists():
            return [".editorconfig base config not found in package data"]
        base = src.read_text()
    except OSError:
        return [".editorconfig base config not found in package data"]
    existing = target.read_text()
    if not verify_hash(existing, base):
        return [".editorconfig has been tampered with — run: ai-guardrails generate"]
    return []


def check_markdownlint(
    configs_dir: Path, registry: ExceptionRegistry, project_dir: Path
) -> list[str]:
    """Return issues if .markdownlint.jsonc is missing or stale."""
    target = project_dir / ".markdownlint.jsonc"
    if not target.exists():
        return [".markdownlint.jsonc is missing — run: ai-guardrails generate"]
    existing = target.read_text()
    try:
        src = configs_dir / ".markdownlint.jsonc"
        if not src.exists():
            return [".markdownlint.jsonc base config not found in package data"]
        raw = src.read_text()
        config = json.loads(strip_jsonc_comments(raw))
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


def check_codespellrc(registry: ExceptionRegistry, project_dir: Path) -> list[str]:
    """Return issues if .codespellrc is missing or stale."""
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


def check_claude_settings(project_dir: Path) -> list[str]:
    """Return issues if .claude/settings.json is missing or tampered."""
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
