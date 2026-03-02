"""Tests for ProjectInfo model."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.models.language import DetectionRules, LanguageConfig
from ai_guardrails.models.project import ProjectInfo


def _python_lang() -> LanguageConfig:
    return LanguageConfig(
        key="python",
        name="Python",
        detect=DetectionRules(files=["pyproject.toml"], patterns=["*.py"], directories=[]),
        configs=["ruff.toml"],
        hook_template="python.yaml",
    )


def test_project_info_stores_root_and_languages(tmp_path: Path) -> None:
    lang = _python_lang()
    proj = ProjectInfo(
        root=tmp_path,
        languages=[lang],
        has_registry=False,
        has_ci=False,
        has_claude_settings=False,
    )
    assert proj.root == tmp_path
    assert len(proj.languages) == 1
    assert proj.languages[0].key == "python"


def test_project_info_has_registry_false_by_default(tmp_path: Path) -> None:
    proj = ProjectInfo(
        root=tmp_path,
        languages=[],
        has_registry=False,
        has_ci=False,
        has_claude_settings=False,
    )
    assert proj.has_registry is False


def test_project_info_has_ci_reflects_github_workflow(tmp_path: Path) -> None:
    ci_path = tmp_path / ".github" / "workflows" / "check.yml"
    ci_path.parent.mkdir(parents=True)
    ci_path.touch()
    proj = ProjectInfo(
        root=tmp_path,
        languages=[],
        has_registry=False,
        has_ci=True,
        has_claude_settings=False,
    )
    assert proj.has_ci is True


def test_project_info_has_claude_settings_reflects_file(tmp_path: Path) -> None:
    proj = ProjectInfo(
        root=tmp_path,
        languages=[],
        has_registry=False,
        has_ci=False,
        has_claude_settings=True,
    )
    assert proj.has_claude_settings is True


def test_project_info_no_languages_is_valid(tmp_path: Path) -> None:
    proj = ProjectInfo(
        root=tmp_path,
        languages=[],
        has_registry=False,
        has_ci=False,
        has_claude_settings=False,
    )
    assert proj.languages == []


def test_project_info_multiple_languages(tmp_path: Path) -> None:
    from ai_guardrails.models.language import DetectionRules, LanguageConfig

    rust = LanguageConfig(
        key="rust",
        name="Rust",
        detect=DetectionRules(files=["Cargo.toml"], patterns=["*.rs"], directories=[]),
        configs=["rustfmt.toml"],
        hook_template="rust.yaml",
    )
    proj = ProjectInfo(
        root=tmp_path,
        languages=[_python_lang(), rust],
        has_registry=False,
        has_ci=False,
        has_claude_settings=False,
    )
    assert len(proj.languages) == 2
