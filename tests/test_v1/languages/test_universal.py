"""Tests for UniversalPlugin — always-active plugin generating universal configs."""

from __future__ import annotations

import json
from pathlib import Path

from ai_guardrails.generators.base import HASH_HEADER_PREFIX, verify_hash
from ai_guardrails.languages.universal import UniversalPlugin
from ai_guardrails.models.registry import ExceptionRegistry


def _make_data_dir(tmp_path: Path) -> Path:
    """Create minimal data_dir with required base configs."""
    data_dir = tmp_path / "data"
    configs_dir = data_dir / "configs"
    configs_dir.mkdir(parents=True)

    (configs_dir / ".editorconfig").write_text(
        "[*]\nend_of_line = lf\ninsert_final_newline = true\n"
    )
    (configs_dir / ".markdownlint.jsonc").write_text(
        '{"default": true, "MD013": false}\n'
    )
    return data_dir


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


def _registry_with_codespell(
    skip: list[str], ignore_words: list[str]
) -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {"codespell": {"skip": skip, "ignore_words": ignore_words}},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


def _registry_with_markdownlint_ignore(rules: list[str]) -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {"markdownlint": {"ignore": rules}},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


# ---------------------------------------------------------------------------
# Plugin attributes
# ---------------------------------------------------------------------------


def test_universal_plugin_key(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    assert plugin.key == "universal"


def test_universal_plugin_name(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    assert plugin.name == "Universal"


def test_universal_plugin_generated_configs_includes_expected(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    configs = plugin.generated_configs
    assert ".editorconfig" in configs
    assert ".markdownlint.jsonc" in configs
    assert ".codespellrc" in configs
    assert ".claude/settings.json" in configs


def test_universal_plugin_copy_files_is_empty(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    assert plugin.copy_files == []


# ---------------------------------------------------------------------------
# detect() — always True
# ---------------------------------------------------------------------------


def test_universal_detect_always_true(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_universal_detect_true_for_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    plugin = UniversalPlugin(tmp_path)
    assert plugin.detect(empty) is True


# ---------------------------------------------------------------------------
# generate() — editorconfig
# ---------------------------------------------------------------------------


def test_generate_produces_editorconfig(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    assert project_dir / ".editorconfig" in outputs


def test_editorconfig_has_hash_header(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / ".editorconfig"]
    assert content.startswith(HASH_HEADER_PREFIX)


def test_editorconfig_hash_is_valid(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    full = outputs[project_dir / ".editorconfig"]
    body = full.split("\n", 1)[1]
    assert verify_hash(full, body)


# ---------------------------------------------------------------------------
# generate() — markdownlint
# ---------------------------------------------------------------------------


def test_generate_produces_markdownlint(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    assert project_dir / ".markdownlint.jsonc" in outputs


def test_markdownlint_has_hash_header(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / ".markdownlint.jsonc"]
    assert content.startswith("// ai-guardrails:hash:sha256:")


def test_markdownlint_merges_registry_ignores(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _registry_with_markdownlint_ignore(["MD001", "MD013"])
    outputs = plugin.generate(registry, project_dir)
    content = outputs[project_dir / ".markdownlint.jsonc"]
    body = content.split("\n", 1)[1]
    parsed = json.loads(body)
    assert parsed.get("MD001") is False
    assert parsed.get("MD013") is False


# ---------------------------------------------------------------------------
# generate() — codespell
# ---------------------------------------------------------------------------


def test_generate_produces_codespellrc(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    assert project_dir / ".codespellrc" in outputs


def test_codespellrc_has_hash_header(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / ".codespellrc"]
    assert content.startswith(HASH_HEADER_PREFIX)


def test_codespellrc_includes_skip_from_registry(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _registry_with_codespell(["*.lock", "vendor/"], [])
    outputs = plugin.generate(registry, project_dir)
    content = outputs[project_dir / ".codespellrc"]
    assert "*.lock" in content
    assert "vendor/" in content


def test_codespellrc_includes_ignore_words_from_registry(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _registry_with_codespell([], ["brin", "crate"])
    outputs = plugin.generate(registry, project_dir)
    content = outputs[project_dir / ".codespellrc"]
    assert "brin" in content
    assert "crate" in content


# ---------------------------------------------------------------------------
# generate() — claude settings
# ---------------------------------------------------------------------------


def test_generate_produces_claude_settings(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    assert project_dir / ".claude" / "settings.json" in outputs


def test_claude_settings_has_hash_header(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / ".claude" / "settings.json"]
    assert content.startswith("// ai-guardrails:hash:sha256:")


def test_claude_settings_has_deny_rules(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / ".claude" / "settings.json"]
    body = content.split("\n", 1)[1]
    parsed = json.loads(body)
    deny = parsed["permissions"]["deny"]
    assert any("Edit" in rule for rule in deny)
    assert any("--no-verify" in rule for rule in deny)


def test_claude_settings_has_pre_tool_use_hook(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / ".claude" / "settings.json"]
    body = content.split("\n", 1)[1]
    parsed = json.loads(body)
    hooks = parsed["hooks"]["PreToolUse"]
    assert len(hooks) > 0
    assert hooks[0]["matcher"] == "Bash"


# ---------------------------------------------------------------------------
# hook_config() — base hooks structure
# ---------------------------------------------------------------------------


def test_hook_config_returns_dict(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    assert isinstance(config, dict)


def test_hook_config_has_pre_commit(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    assert "pre-commit" in config


def test_hook_config_has_suppress_comments_command(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    commands = config["pre-commit"]["commands"]
    assert "suppress-comments" in commands


def test_hook_config_has_protect_configs_command(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    commands = config["pre-commit"]["commands"]
    assert "protect-configs" in commands


def test_hook_config_has_codespell_command(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    commands = config["pre-commit"]["commands"]
    assert "codespell" in commands


def test_hook_config_has_markdownlint_command(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    commands = config["pre-commit"]["commands"]
    assert "markdownlint" in commands


def test_hook_config_has_commit_msg_section(tmp_path: Path) -> None:
    plugin = UniversalPlugin(tmp_path)
    config = plugin.hook_config()
    assert "commit-msg" in config


# ---------------------------------------------------------------------------
# check() — validates generated files
# ---------------------------------------------------------------------------


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _empty_registry()
    outputs = plugin.generate(registry, project_dir)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    assert plugin.check(registry, project_dir) == []


def test_check_reports_missing_editorconfig(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    issues = plugin.check(_empty_registry(), project_dir)
    missing = [i for i in issues if ".editorconfig" in i]
    assert len(missing) >= 1


def test_check_reports_missing_markdownlint(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    issues = plugin.check(_empty_registry(), project_dir)
    missing = [i for i in issues if ".markdownlint.jsonc" in i]
    assert len(missing) >= 1


def test_check_reports_missing_codespellrc(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    issues = plugin.check(_empty_registry(), project_dir)
    missing = [i for i in issues if ".codespellrc" in i]
    assert len(missing) >= 1


def test_check_reports_tampered_editorconfig(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _empty_registry()
    outputs = plugin.generate(registry, project_dir)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    # Tamper with editorconfig
    (project_dir / ".editorconfig").write_text("# tampered\n[*]\nindent_size = 2\n")
    issues = plugin.check(registry, project_dir)
    tampered = [i for i in issues if ".editorconfig" in i]
    assert len(tampered) >= 1


def test_check_markdownlint_detects_tampered_body(tmp_path: Path) -> None:
    """Appending to markdownlint body must be detected even when header hash matches."""
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _empty_registry()
    outputs = plugin.generate(registry, project_dir)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    # Append tamper content after the body (header stays intact)
    target = project_dir / ".markdownlint.jsonc"
    original = target.read_text()
    target.write_text(original + "TAMPERED")
    issues = plugin.check(registry, project_dir)
    tampered = [i for i in issues if ".markdownlint.jsonc" in i]
    assert len(tampered) >= 1


def test_check_claude_settings_detects_tampered_body(tmp_path: Path) -> None:
    """Appending to settings body must be detected even when header hash matches."""
    data_dir = _make_data_dir(tmp_path)
    plugin = UniversalPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _empty_registry()
    outputs = plugin.generate(registry, project_dir)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    # Append tamper content after the body (header stays intact)
    target = project_dir / ".claude" / "settings.json"
    original = target.read_text()
    target.write_text(original + "TAMPERED")
    issues = plugin.check(registry, project_dir)
    tampered = [i for i in issues if ".claude/settings.json" in i]
    assert len(tampered) >= 1
