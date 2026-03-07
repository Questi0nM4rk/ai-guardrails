"""Tests for BaseLanguagePlugin detection logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

from ai_guardrails.languages._base import BaseLanguagePlugin, LanguagePlugin

# ---------------------------------------------------------------------------
# Concrete test plugin
# ---------------------------------------------------------------------------


class _PythonLike(BaseLanguagePlugin):
    key = "python"
    name = "Python"
    detect_files: ClassVar[list[str]] = [
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
    ]
    detect_patterns: ClassVar[list[str]] = ["*.py"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = ["ruff.toml"]

    def __init__(self) -> None:
        pass

    def generate(self, registry, project_dir):  # type: ignore[override]
        return {}


class _DirPlugin(BaseLanguagePlugin):
    """Plugin that detects by directory presence."""

    key = "lua"
    name = "Lua"
    detect_files: ClassVar[list[str]] = []
    detect_patterns: ClassVar[list[str]] = ["*.lua"]
    detect_dirs: ClassVar[list[str]] = ["lua"]
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = ["stylua.toml"]

    def __init__(self) -> None:
        pass

    def generate(self, registry, project_dir):  # type: ignore[override]
        return {}


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


def test_base_plugin_satisfies_protocol() -> None:
    plugin = _PythonLike()
    assert isinstance(plugin, LanguagePlugin)


# ---------------------------------------------------------------------------
# detect() via detect_files
# ---------------------------------------------------------------------------


def test_detect_returns_true_for_exact_file_match(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is True


def test_detect_returns_false_when_no_indicator_files(tmp_path: Path) -> None:
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is False


def test_detect_matches_any_detect_file(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text("# setup\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is True


def test_detect_matches_requirements_txt(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is True


# ---------------------------------------------------------------------------
# detect() via detect_patterns (glob, skip dirs)
# ---------------------------------------------------------------------------


def test_detect_returns_true_for_pattern_match(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("# python\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is True


def test_detect_skips_venv_directory(tmp_path: Path) -> None:
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "something.py").write_text("# hidden\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is False


def test_detect_skips_node_modules(tmp_path: Path) -> None:
    nm = tmp_path / "node_modules" / "some_pkg"
    nm.mkdir(parents=True)
    (nm / "index.py").write_text("# hidden\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is False


def test_detect_skips_git_directory(tmp_path: Path) -> None:
    git = tmp_path / ".git" / "hooks"
    git.mkdir(parents=True)
    (git / "pre-commit.py").write_text("# hidden\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is False


def test_detect_skips_pycache(tmp_path: Path) -> None:
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "module.py").write_text("# cached\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is False


def test_detect_finds_py_file_outside_skip_dirs(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("# app\n")
    plugin = _PythonLike()
    assert plugin.detect(tmp_path) is True


# ---------------------------------------------------------------------------
# detect() via detect_dirs
# ---------------------------------------------------------------------------


def test_detect_returns_true_for_directory_presence(tmp_path: Path) -> None:
    (tmp_path / "lua").mkdir()
    plugin = _DirPlugin()
    assert plugin.detect(tmp_path) is True


def test_detect_returns_false_when_directory_absent(tmp_path: Path) -> None:
    plugin = _DirPlugin()
    assert plugin.detect(tmp_path) is False


# ---------------------------------------------------------------------------
# fixtures dir skip
# ---------------------------------------------------------------------------


class _GoLike(BaseLanguagePlugin):
    """Plugin that detects Go via go.mod pattern."""

    key = "go"
    name = "Go"
    detect_files: ClassVar[list[str]] = []
    detect_patterns: ClassVar[list[str]] = ["go.mod"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = []

    def __init__(self) -> None:
        pass

    def generate(self, registry, project_dir):  # type: ignore[override]
        return {}


def test_detect_skips_fixtures_directory(tmp_path: Path) -> None:
    """Files under tests/fixtures/ must not trigger language detection."""
    fixture_dir = tmp_path / "tests" / "fixtures" / "go-bad"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "go.mod").write_text("module example.com/bad\n")

    plugin = _GoLike()
    assert plugin.detect(tmp_path) is False


# ---------------------------------------------------------------------------
# check() default
# ---------------------------------------------------------------------------


def test_check_returns_empty_list_by_default(tmp_path: Path) -> None:
    from ai_guardrails.models.registry import ExceptionRegistry  # noqa: PLC0415

    registry = ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )
    plugin = _PythonLike()
    assert plugin.check(registry, tmp_path) == []
