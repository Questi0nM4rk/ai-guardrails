"""Tests for CodespellGenerator — generated from registry global_rules."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.generators.codespell import CodespellGenerator
from ai_guardrails.models.registry import ExceptionRegistry


def _make_registry(codespell_config: dict) -> ExceptionRegistry:  # type: ignore[type-arg]
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {"codespell": codespell_config},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


def _empty_registry() -> ExceptionRegistry:
    return _make_registry({})


def test_codespell_generator_name() -> None:
    assert CodespellGenerator().name == "codespell"


def test_codespell_generator_output_files() -> None:
    assert CodespellGenerator().output_files == [".codespellrc"]


def test_generate_minimal_output_contains_section_header(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    result = gen.generate(_empty_registry(), [], tmp_path)

    content = result[tmp_path / ".codespellrc"]
    assert "[codespell]" in content


def test_generate_output_has_hash_header(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    result = gen.generate(_empty_registry(), [], tmp_path)
    content = next(iter(result.values()))
    assert content.startswith("# ai-guardrails:hash:sha256:")


def test_generate_includes_skip_from_registry(tmp_path: Path) -> None:
    registry = _make_registry({"skip": ["*.lock", "*.min.js"]})
    gen = CodespellGenerator()
    result = gen.generate(registry, [], tmp_path)
    content = result[tmp_path / ".codespellrc"]
    assert "skip = *.lock,*.min.js" in content


def test_generate_includes_ignore_words_from_registry(tmp_path: Path) -> None:
    registry = _make_registry({"ignore_words": ["brin", "crate"]})
    gen = CodespellGenerator()
    result = gen.generate(registry, [], tmp_path)
    content = result[tmp_path / ".codespellrc"]
    assert "ignore-words-list = brin,crate" in content


def test_generate_omits_skip_when_empty(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    result = gen.generate(_empty_registry(), [], tmp_path)
    content = next(iter(result.values()))
    assert "skip" not in content


def test_generate_omits_ignore_words_when_empty(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    result = gen.generate(_empty_registry(), [], tmp_path)
    content = next(iter(result.values()))
    assert "ignore-words-list" not in content


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    registry = _make_registry({"ignore_words": ["brin"]})
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    generated = gen.generate(registry, [], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    assert gen.check(registry, project_dir) == []


def test_check_returns_issue_when_missing(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    issues = gen.check(_empty_registry(), project_dir)
    assert len(issues) == 1
    assert ".codespellrc" in issues[0]


def test_check_returns_issue_when_tampered(tmp_path: Path) -> None:
    gen = CodespellGenerator()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / ".codespellrc").write_text("# ai-guardrails:hash:sha256:badhash\n[codespell]\n")

    issues = gen.check(_empty_registry(), project_dir)
    assert len(issues) == 1
    assert ".codespellrc" in issues[0]
