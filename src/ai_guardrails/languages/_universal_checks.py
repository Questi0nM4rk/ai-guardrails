"""Generate and check helpers for UniversalPlugin.

Extracted to keep universal.py under the 200-line module limit.
Each function either builds or verifies one generated config file.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ai_guardrails.constants import GENERATED_CONFIGS
from ai_guardrails.generators.base import compute_hash, make_hash_header, verify_hash

if TYPE_CHECKING:
    from pathlib import Path

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
    body = json.dumps(config, indent=2) + "\n"
    header = f"{_JSONC_HASH_PREFIX}{compute_hash(body)}"
    return project_dir / ".markdownlint.jsonc", f"{header}\n{body}"


def _build_codespellrc_body(registry: ExceptionRegistry) -> str:
    """Return the expected .codespellrc content body."""
    codespell_config = registry.global_rules.get("codespell", {})
    lines = ["[codespell]"]
    skip = codespell_config.get("skip", [])
    if skip:
        lines.append(f"skip = {','.join(skip)}")
    ignore_words = codespell_config.get("ignore_words", [])
    if ignore_words:
        lines.append(f"ignore-words-list = {','.join(ignore_words)}")
    lines.append("")
    return "\n".join(lines)


def generate_codespellrc(
    registry: ExceptionRegistry, project_dir: Path
) -> tuple[Path, str]:
    """Return (path, content) for .codespellrc from registry."""
    body = _build_codespellrc_body(registry)
    header = make_hash_header(body)
    return project_dir / ".codespellrc", f"{header}\n{body}"


def _build_claude_settings_body() -> str:
    """Return the expected .claude/settings.json content body."""
    edit_rules = [f"Edit({cfg})" for cfg in sorted(GENERATED_CONFIGS)]
    bash_rules = [
        "Bash(* --no-verify *)",
        "Bash(git commit * -n *)",
        "Bash(git push --force *)",
        "Bash(git push * --force *)",
    ]
    pre_tool_hook = {
        "type": "command",
        "command": "uv run python -m ai_guardrails.hooks.dangerous_cmd",
    }
    settings = {
        "permissions": {"deny": edit_rules + bash_rules},
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [pre_tool_hook]}]},
    }
    return json.dumps(settings, indent=2) + "\n"


def generate_claude_settings(project_dir: Path) -> tuple[Path, str]:
    """Return (path, content) for .claude/settings.json with deny rules."""
    body = _build_claude_settings_body()
    header = f"{_JSONC_HASH_PREFIX}{compute_hash(body)}"
    return project_dir / ".claude" / "settings.json", f"{header}\n{body}"


def _verify_jsonc_hash(existing: str, expected_body: str) -> bool:
    """Return True if the JSONC hash header is valid and content matches expected.

    Checks both tamper (actual body vs stored hash) and staleness (expected
    body vs stored hash). Returns False if either check fails.
    """
    first_line = existing.split("\n", 1)[0].strip()
    if not first_line.startswith(_JSONC_HASH_PREFIX):
        return False
    stored_hash = first_line[len(_JSONC_HASH_PREFIX) :]
    actual_body = existing.split("\n", 1)[1] if "\n" in existing else ""
    return stored_hash == compute_hash(actual_body) == compute_hash(expected_body)


def check_editorconfig(configs_dir: Path, project_dir: Path) -> list[str]:
    """Return issues if .editorconfig is missing or tampered."""
    target = project_dir / ".editorconfig"
    if not target.exists():
        return [".editorconfig is missing — run: ai-guardrails generate"]
    try:
        src = configs_dir / ".editorconfig"
        base = src.read_text() if src.exists() else None
    except OSError:
        base = None
    if base is None:
        return [".editorconfig base config not found in package data"]
    existing = target.read_text()
    if not verify_hash(existing, base):
        return [".editorconfig has been tampered with — run: ai-guardrails generate"]
    return []


def check_markdownlint(
    configs_dir: Path, registry: ExceptionRegistry, project_dir: Path
) -> list[str]:
    """Return issues if .markdownlint.jsonc is missing or stale."""
    _stale = ".markdownlint.jsonc is stale or tampered — run: ai-guardrails generate"
    target = project_dir / ".markdownlint.jsonc"
    if not target.exists():
        return [".markdownlint.jsonc is missing — run: ai-guardrails generate"]
    existing = target.read_text()
    expected_body = _build_markdownlint_body(configs_dir, registry)
    if expected_body is None:
        return [".markdownlint.jsonc base config not found in package data"]
    if not _verify_jsonc_hash(existing, expected_body):
        return [_stale]
    return []


def _build_markdownlint_body(
    configs_dir: Path, registry: ExceptionRegistry
) -> str | None:
    """Return the expected markdownlint body, or None if the base config is missing."""
    try:
        src = configs_dir / ".markdownlint.jsonc"
        if not src.exists():
            return None
        raw = src.read_text()
        config = json.loads(strip_jsonc_comments(raw))
        for rule in registry.get_ignores("markdownlint"):
            config[rule] = False
        return json.dumps(config, indent=2) + "\n"
    except (OSError, json.JSONDecodeError):
        return None


def check_codespellrc(registry: ExceptionRegistry, project_dir: Path) -> list[str]:
    """Return issues if .codespellrc is missing or stale."""
    target = project_dir / ".codespellrc"
    if not target.exists():
        return [".codespellrc is missing — run: ai-guardrails generate"]
    existing = target.read_text()
    expected_body = _build_codespellrc_body(registry)
    if not verify_hash(existing, expected_body):
        return [".codespellrc is stale or tampered — run: ai-guardrails generate"]
    return []


def check_claude_settings(project_dir: Path) -> list[str]:
    """Return issues if .claude/settings.json is missing or tampered."""
    _stale = ".claude/settings.json is stale or tampered — run: ai-guardrails generate"
    target = project_dir / ".claude" / "settings.json"
    if not target.exists():
        return [".claude/settings.json is missing — run: ai-guardrails generate"]
    existing = target.read_text()
    expected_body = _build_claude_settings_body()
    if not _verify_jsonc_hash(existing, expected_body):
        return [_stale]
    return []
