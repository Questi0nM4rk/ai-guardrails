"""Tests for LefthookGenerator — assembles lefthook.yml from language templates."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_guardrails.generators.lefthook import LefthookGenerator
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


def _make_templates_dir(tmp_path: Path) -> Path:
    """Create minimal lefthook templates for testing."""
    templates_dir = tmp_path / "lefthook"
    templates_dir.mkdir(parents=True)

    base = {
        "pre-commit": {
            "commands": {
                "codespell": {
                    "glob": "*.{py,md}",
                    "run": "codespell {staged_files}",
                    "priority": 2,
                },
                "markdownlint": {
                    "glob": "*.md",
                    "run": "markdownlint-cli2 {staged_files}",
                    "priority": 2,
                },
            }
        },
        "commit-msg": {
            "commands": {
                "conventional": {
                    "run": 'echo "{1}" | grep -qE "^(feat|fix):"',
                }
            }
        },
    }
    (templates_dir / "base.yaml").write_text(yaml.dump(base))

    python_hooks = {
        "pre-commit": {
            "commands": {
                "python-format-and-stage": {
                    "glob": "*.py",
                    "run": "ruff format {staged_files} && git add {staged_files}",
                    "stage_fixed": True,
                    "priority": 1,
                },
                "ruff-check": {
                    "glob": "*.py",
                    "run": "ruff check {staged_files}",
                    "priority": 2,
                },
            }
        }
    }
    (templates_dir / "python.yaml").write_text(yaml.dump(python_hooks))

    node_hooks = {
        "pre-commit": {
            "commands": {
                "node-format-and-stage": {
                    "glob": "*.{js,ts}",
                    "run": "biome check --apply {staged_files} && git add {staged_files}",
                    "stage_fixed": True,
                    "priority": 1,
                },
                "biome-check": {
                    "glob": "*.{js,ts}",
                    "run": "biome check {staged_files}",
                    "priority": 2,
                },
            }
        }
    }
    (templates_dir / "node.yaml").write_text(yaml.dump(node_hooks))

    return templates_dir


def test_lefthook_generator_name(tmp_path: Path) -> None:
    gen = LefthookGenerator(templates_dir=tmp_path)
    assert gen.name == "lefthook"


def test_lefthook_generator_output_files(tmp_path: Path) -> None:
    gen = LefthookGenerator(templates_dir=tmp_path)
    assert gen.output_files == ["lefthook.yml"]


def test_generate_output_has_hash_header(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = result[project_dir / "lefthook.yml"]
    assert content.startswith("# ai-guardrails:hash:sha256:")


def test_generate_base_commands_always_present(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = result[project_dir / "lefthook.yml"]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)

    commands = parsed["pre-commit"]["commands"]
    assert "codespell" in commands
    assert "markdownlint" in commands


def test_generate_commit_msg_present(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), [], project_dir)
    content = result[project_dir / "lefthook.yml"]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)

    assert "commit-msg" in parsed


def test_generate_merges_python_hooks_when_detected(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), ["python"], project_dir)
    content = result[project_dir / "lefthook.yml"]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)

    commands = parsed["pre-commit"]["commands"]
    assert "python-format-and-stage" in commands
    assert "ruff-check" in commands
    # Base commands still present
    assert "codespell" in commands


def test_generate_merges_node_hooks_when_detected(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), ["node"], project_dir)
    content = result[project_dir / "lefthook.yml"]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)

    commands = parsed["pre-commit"]["commands"]
    assert "node-format-and-stage" in commands
    assert "biome-check" in commands


def test_generate_merges_multiple_languages(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(_empty_registry(), ["python", "node"], project_dir)
    content = result[project_dir / "lefthook.yml"]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)

    commands = parsed["pre-commit"]["commands"]
    assert "python-format-and-stage" in commands
    assert "ruff-check" in commands
    assert "node-format-and-stage" in commands
    assert "biome-check" in commands
    assert "codespell" in commands


def test_generate_skips_missing_language_template(tmp_path: Path) -> None:
    """Unknown language keys that have no template file are silently skipped."""
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # "rust" has no template in our test setup — should not raise
    result = gen.generate(_empty_registry(), ["python", "rust"], project_dir)
    content = result[project_dir / "lefthook.yml"]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)

    commands = parsed["pre-commit"]["commands"]
    assert "python-format-and-stage" in commands
    assert "ruff-check" in commands


def test_generate_raises_if_base_template_missing(tmp_path: Path) -> None:
    templates_dir = tmp_path / "lefthook"
    templates_dir.mkdir()
    # No base.yaml
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        gen.generate(_empty_registry(), [], project_dir)


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    registry = _empty_registry()
    generated = gen.generate(registry, ["python"], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    assert gen.check(registry, project_dir) == []


def test_check_returns_issue_when_missing(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    issues = gen.check(_empty_registry(), project_dir)
    assert len(issues) == 1
    assert "lefthook.yml" in issues[0]


def test_check_returns_issue_when_tampered(tmp_path: Path) -> None:
    templates_dir = _make_templates_dir(tmp_path)
    gen = LefthookGenerator(templates_dir=templates_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "lefthook.yml").write_text(
        "# ai-guardrails:hash:sha256:badhash\npre-commit:\n  commands: {}\n"
    )

    issues = gen.check(_empty_registry(), project_dir)
    assert len(issues) == 1
    assert "lefthook.yml" in issues[0]
