"""Tests for EditorconfigGenerator — pure copy, no exception merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.generators.editorconfig import EditorconfigGenerator
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


def _make_generator(configs_dir: Path) -> EditorconfigGenerator:
    return EditorconfigGenerator(configs_dir=configs_dir)


def test_editorconfig_generator_name() -> None:
    gen = _make_generator(Path("/configs"))
    assert gen.name == "editorconfig"


def test_editorconfig_generator_output_files() -> None:
    gen = _make_generator(Path("/configs"))
    assert gen.output_files == [".editorconfig"]


def test_generate_returns_editorconfig_content(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    src = configs_dir / ".editorconfig"
    src.write_text("root = true\n[*]\nindent_size = 4\n")

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(registry, [], project_dir)

    assert len(result) == 1
    output_path = project_dir / ".editorconfig"
    assert output_path in result
    assert "root = true" in result[output_path]


def test_generate_output_includes_hash_header(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / ".editorconfig").write_text("root = true\n")

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = gen.generate(registry, [], project_dir)
    content = next(iter(result.values()))
    assert content.startswith("# ai-guardrails:hash:sha256:")


def test_generate_languages_arg_ignored(tmp_path: Path) -> None:
    """Editorconfig applies to all languages — languages list is irrelevant."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / ".editorconfig").write_text("root = true\n")

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result_empty = gen.generate(registry, [], project_dir)
    result_python = gen.generate(registry, ["python"], project_dir)

    assert next(iter(result_empty.values())) == next(iter(result_python.values()))


def test_generate_raises_if_base_missing(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    # No .editorconfig in configs_dir

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        gen.generate(registry, [], project_dir)


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    base_content = "root = true\n"
    (configs_dir / ".editorconfig").write_text(base_content)

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Write the correct generated content to project
    generated = gen.generate(registry, [], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    issues = gen.check(registry, project_dir)
    assert issues == []


def test_check_returns_issue_when_missing(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / ".editorconfig").write_text("root = true\n")

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    issues = gen.check(registry, project_dir)
    assert len(issues) == 1
    assert ".editorconfig" in issues[0]


def test_check_returns_issue_when_tampered(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / ".editorconfig").write_text("root = true\n")

    gen = _make_generator(configs_dir)
    registry = _empty_registry()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Write tampered content
    (project_dir / ".editorconfig").write_text("# ai-guardrails:hash:sha256:badhash\ntampered\n")

    issues = gen.check(registry, project_dir)
    assert len(issues) == 1
    assert "tampered" in issues[0].lower() or ".editorconfig" in issues[0]
