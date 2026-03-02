"""Tests for MarkdownlintGenerator — merges base .markdownlint.jsonc with registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_guardrails.generators.markdownlint import MarkdownlintGenerator
from ai_guardrails.models.registry import ExceptionRegistry


def _make_registry(ignore_rules: list[str] | None = None) -> ExceptionRegistry:
    global_rules = {}
    if ignore_rules:
        global_rules = {"markdownlint": {"ignore": ignore_rules}}
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": global_rules,
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


def _write_base_jsonc(dir: Path, content: str) -> Path:
    path = dir / ".markdownlint.jsonc"
    path.write_text(content)
    return path


BASE_JSONC = """{
  "default": true,
  "MD013": false,
  "MD041": true
}
"""

JSONC_WITH_COMMENTS = """// Markdownlint config
{
  "default": true,
  // MD013: line length
  "MD013": false
}
"""


def test_markdownlint_generator_name(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator(configs_dir=tmp_path)
    assert gen.name == "markdownlint"


def test_markdownlint_generator_output_files(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator(configs_dir=tmp_path)
    assert gen.output_files == [".markdownlint.jsonc"]


def test_generate_returns_jsonc_with_hash_header(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, BASE_JSONC)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_make_registry(), [], project_dir)
    content = result[project_dir / ".markdownlint.jsonc"]
    assert content.startswith("// ai-guardrails:hash:sha256:")


def test_generate_preserves_base_config_values(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, BASE_JSONC)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_make_registry(), [], project_dir)
    content = result[project_dir / ".markdownlint.jsonc"]

    # Strip hash header line to get JSON
    lines = content.split("\n", 1)
    json_body = lines[1] if len(lines) > 1 else lines[0]
    parsed = json.loads(json_body)
    assert parsed["default"] is True
    assert parsed["MD013"] is False


def test_generate_disables_ignored_rules(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, BASE_JSONC)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    registry = _make_registry(ignore_rules=["MD041", "MD001"])
    result = gen.generate(registry, [], project_dir)
    content = result[project_dir / ".markdownlint.jsonc"]

    lines = content.split("\n", 1)
    json_body = lines[1] if len(lines) > 1 else lines[0]
    parsed = json.loads(json_body)
    assert parsed["MD041"] is False
    assert parsed["MD001"] is False


def test_generate_strips_jsonc_comments(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, JSONC_WITH_COMMENTS)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_make_registry(), [], project_dir)
    content = result[project_dir / ".markdownlint.jsonc"]

    lines = content.split("\n", 1)
    json_body = lines[1] if len(lines) > 1 else lines[0]
    parsed = json.loads(json_body)
    assert parsed["default"] is True


def test_generate_raises_if_base_missing(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        gen.generate(_make_registry(), [], project_dir)


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, BASE_JSONC)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    registry = _make_registry()
    generated = gen.generate(registry, [], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    assert gen.check(registry, project_dir) == []


def test_check_returns_issue_when_missing(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, BASE_JSONC)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    issues = gen.check(_make_registry(), project_dir)
    assert len(issues) == 1
    assert ".markdownlint.jsonc" in issues[0]


def test_check_returns_issue_when_stale(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_jsonc(configs_dir, BASE_JSONC)
    gen = MarkdownlintGenerator(configs_dir=configs_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Generate without any ignore rules
    registry_v1 = _make_registry()
    generated = gen.generate(registry_v1, [], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    # Now check with a different registry (more ignored rules)
    registry_v2 = _make_registry(ignore_rules=["MD001"])
    issues = gen.check(registry_v2, project_dir)
    assert len(issues) == 1
    assert ".markdownlint.jsonc" in issues[0]
