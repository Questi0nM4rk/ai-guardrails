"""Tests for DetectLanguagesStep."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.infra.config_loader import ConfigLoader
from ai_guardrails.languages._base import BaseLanguagePlugin, LanguagePlugin
from ai_guardrails.pipelines.base import PipelineContext
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from tests.test_v1.conftest import FakeCommandRunner, FakeConsole, FakeFileManager

# ---------------------------------------------------------------------------
# Test double plugins
# ---------------------------------------------------------------------------


class _AlwaysPlugin(BaseLanguagePlugin):
    """Plugin that always detects."""

    key = "always"
    name = "Always"
    copy_files: list[str] = []
    generated_configs: list[str] = []

    def __init__(self) -> None:
        pass

    def detect(self, project_dir: Path) -> bool:
        return True


class _NeverPlugin(BaseLanguagePlugin):
    """Plugin that never detects."""

    key = "never"
    name = "Never"
    copy_files: list[str] = []
    generated_configs: list[str] = []

    def __init__(self) -> None:
        pass

    def detect(self, project_dir: Path) -> bool:
        return False


class _PythonPlugin(BaseLanguagePlugin):
    key = "python"
    name = "Python"
    detect_files = ["pyproject.toml", "setup.py", "requirements.txt"]
    detect_patterns = ["*.py"]
    detect_dirs: list[str] = []
    copy_files: list[str] = []
    generated_configs = ["ruff.toml"]

    def __init__(self) -> None:
        pass


class _RustPlugin(BaseLanguagePlugin):
    key = "rust"
    name = "Rust"
    detect_files = ["Cargo.toml"]
    detect_patterns = ["*.rs"]
    detect_dirs: list[str] = []
    copy_files = ["rustfmt.toml"]
    generated_configs: list[str] = []

    def __init__(self) -> None:
        pass


def _make_context(project_dir: Path) -> PipelineContext:
    fm = FakeFileManager()
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
    step = DetectLanguagesStep(plugins=[])
    assert step.name == "detect-languages"


def test_detect_languages_validate_always_passes(tmp_path: Path) -> None:
    step = DetectLanguagesStep(plugins=[])
    ctx = _make_context(tmp_path)
    assert step.validate(ctx) == []


def test_detect_always_active_plugin(tmp_path: Path) -> None:
    step = DetectLanguagesStep(plugins=[_AlwaysPlugin()])
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    assert len(ctx.languages) == 1
    assert ctx.languages[0].key == "always"


def test_detect_never_active_plugin_returns_warn(tmp_path: Path) -> None:
    step = DetectLanguagesStep(plugins=[_NeverPlugin()])
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "warn"
    assert ctx.languages == []


def test_detect_python_by_pyproject_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    step = DetectLanguagesStep(plugins=[_PythonPlugin()])
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    keys = [p.key for p in ctx.languages]
    assert "python" in keys


def test_detect_rust_by_cargo_toml(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
    step = DetectLanguagesStep(plugins=[_RustPlugin()])
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "ok"
    keys = [p.key for p in ctx.languages]
    assert "rust" in keys


def test_detect_multiple_languages(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "Cargo.toml").write_text("[package]\n")
    step = DetectLanguagesStep(plugins=[_PythonPlugin(), _RustPlugin()])
    ctx = _make_context(tmp_path)
    step.execute(ctx)
    keys = [p.key for p in ctx.languages]
    assert "python" in keys
    assert "rust" in keys


def test_detect_no_languages_returns_warn(tmp_path: Path) -> None:
    step = DetectLanguagesStep(plugins=[_PythonPlugin()])
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert result.status == "warn"
    assert ctx.languages == []


def test_detect_updates_context_languages(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    step = DetectLanguagesStep(plugins=[_PythonPlugin()])
    ctx = _make_context(tmp_path)
    step.execute(ctx)
    assert len(ctx.languages) >= 1
    assert all(isinstance(lang, LanguagePlugin) for lang in ctx.languages)


def test_detect_skips_venv_directory(tmp_path: Path) -> None:
    """Files in .venv should not trigger language detection."""
    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "pyproject.toml").write_text("[project]\n")
    step = DetectLanguagesStep(plugins=[_PythonPlugin()])
    ctx = _make_context(tmp_path)
    step.execute(ctx)
    keys = [p.key for p in ctx.languages]
    assert "python" not in keys


def test_detect_message_includes_detected_names(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    step = DetectLanguagesStep(plugins=[_PythonPlugin()])
    ctx = _make_context(tmp_path)
    result = step.execute(ctx)
    assert "Python" in result.message
