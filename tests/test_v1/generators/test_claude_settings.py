"""Tests for ClaudeSettingsGenerator — generates .claude/settings.json."""

from __future__ import annotations

import json
from pathlib import Path

from ai_guardrails.generators.claude_settings import ClaudeSettingsGenerator
from ai_guardrails.models.registry import ExceptionRegistry


def _empty_registry() -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


def test_claude_settings_generator_name() -> None:
    assert ClaudeSettingsGenerator().name == "claude_settings"


def test_claude_settings_generator_output_files() -> None:
    assert ClaudeSettingsGenerator().output_files == [".claude/settings.json"]


def test_generate_returns_claude_settings_json(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    output_path = project_dir / ".claude" / "settings.json"
    assert output_path in result


def test_generate_output_is_valid_json(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = list(result.values())[0]

    # Strip hash comment header
    body = "\n".join(line for line in content.split("\n") if not line.startswith("//"))
    parsed = json.loads(body)
    assert isinstance(parsed, dict)


def test_generate_includes_permissions_deny_for_generated_configs(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = list(result.values())[0]
    body = "\n".join(line for line in content.split("\n") if not line.startswith("//"))
    parsed = json.loads(body)

    deny_rules = parsed["permissions"]["deny"]
    assert any("ruff.toml" in rule for rule in deny_rules)
    assert any("lefthook.yml" in rule for rule in deny_rules)
    assert any(".editorconfig" in rule for rule in deny_rules)
    assert any(".markdownlint.jsonc" in rule for rule in deny_rules)
    assert any(".codespellrc" in rule for rule in deny_rules)


def test_generate_includes_no_verify_deny_rule(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = list(result.values())[0]
    body = "\n".join(line for line in content.split("\n") if not line.startswith("//"))
    parsed = json.loads(body)

    deny_rules = parsed["permissions"]["deny"]
    assert any("--no-verify" in rule for rule in deny_rules)


def test_generate_includes_force_push_deny_rule(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = list(result.values())[0]
    body = "\n".join(line for line in content.split("\n") if not line.startswith("//"))
    parsed = json.loads(body)

    deny_rules = parsed["permissions"]["deny"]
    assert any("--force" in rule for rule in deny_rules)


def test_generate_includes_pretooluse_hook(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = list(result.values())[0]
    body = "\n".join(line for line in content.split("\n") if not line.startswith("//"))
    parsed = json.loads(body)

    hooks = parsed.get("hooks", {})
    pre_tool_hooks = hooks.get("PreToolUse", [])
    assert len(pre_tool_hooks) > 0
    bash_hooks = [h for h in pre_tool_hooks if h.get("matcher") == "Bash"]
    assert len(bash_hooks) > 0


def test_generate_output_has_hash_header(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = list(result.values())[0]
    assert content.startswith("// ai-guardrails:hash:sha256:")


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    registry = _empty_registry()
    generated = gen.generate(registry, [], project_dir)
    for path, content in generated.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    assert gen.check(registry, project_dir) == []


def test_check_returns_issue_when_missing(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    issues = gen.check(_empty_registry(), project_dir)
    assert len(issues) == 1
    assert "settings.json" in issues[0]


def test_check_returns_issue_when_tampered(tmp_path: Path) -> None:
    gen = ClaudeSettingsGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()

    (claude_dir / "settings.json").write_text(
        '// ai-guardrails:hash:sha256:badhash\n{"permissions": {"deny": []}}\n'
    )

    issues = gen.check(_empty_registry(), project_dir)
    assert len(issues) == 1
    assert "settings.json" in issues[0]
