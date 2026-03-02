"""Tests for DetectLanguagesStep."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.models.language import LanguageConfig
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

# Path to the real languages.yaml for integration tests
_LANGUAGES_YAML = Path(__file__).parents[3] / "configs" / "languages.yaml"


def _make_context(
    project_dir: Path,
    files: dict[Path, str] | None = None,
    languages_yaml: Path | None = None,
) -> PipelineContext:
    fm = FakeFileManager()
    if files:
        for path, content in files.items():
            fm.seed(path, content)
    return PipelineContext(
        project_dir=project_dir,
        file_manager=fm,
        command_runner=FakeCommandRunner(),
        config_loader=ConfigLoader(),
        console=FakeConsole(),
        languages=[],
        registry=None,
        dry_run=False,
        force=False,
    )


def test_detect_languages_step_name() -> None:
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    assert step.name == "detect-languages"


def test_detect_languages_validate_passes_when_yaml_exists() -> None:
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(Path("/project"))
    assert step.validate(ctx) == []


def test_detect_languages_validate_fails_when_yaml_missing(tmp_path: Path) -> None:
    step = DetectLanguagesStep(languages_yaml=tmp_path / "missing.yaml")
    ctx = _make_context(tmp_path)
    errors = step.validate(ctx)
    assert len(errors) == 1
    assert "languages.yaml" in errors[0]


def test_detect_python_by_pyproject_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    keys = [lang.key for lang in ctx.languages]
    assert "python" in keys


def test_detect_rust_by_cargo_toml(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    keys = [lang.key for lang in ctx.languages]
    assert "rust" in keys


def test_detect_node_by_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    keys = [lang.key for lang in ctx.languages]
    assert "node" in keys


def test_detect_multiple_languages(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "Cargo.toml").write_text("[package]\n")
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    step.execute(ctx)
    keys = [lang.key for lang in ctx.languages]
    assert "python" in keys
    assert "rust" in keys


def test_detect_no_languages_returns_warn(tmp_path: Path) -> None:
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "warn"
    assert ctx.languages == []


def test_detect_updates_context_languages(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    step.execute(ctx)
    assert len(ctx.languages) >= 1
    assert all(isinstance(lang, LanguageConfig) for lang in ctx.languages)


def test_detect_skips_venv_directory(tmp_path: Path) -> None:
    """Files in .venv should not trigger language detection."""
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "pyproject.toml").write_text("[project]\n")
    # But no pyproject.toml in root
    step = DetectLanguagesStep(languages_yaml=_LANGUAGES_YAML)
    ctx = _make_context(tmp_path)
    step.execute(ctx)
    keys = [lang.key for lang in ctx.languages]
    assert "python" not in keys
