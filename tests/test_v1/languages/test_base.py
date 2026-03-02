"""Tests for BaseLanguagePlugin detection logic."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.languages._base import BaseLanguagePlugin, LanguagePlugin

# ---------------------------------------------------------------------------
# Concrete test plugin
# ---------------------------------------------------------------------------


class _PythonLike(BaseLanguagePlugin):
    key = "python"
    name = "Python"
    detect_files = ["pyproject.toml", "setup.py", "requirements.txt"]
    detect_patterns = ["*.py"]
    detect_dirs: list[str] = []
    copy_files: list[str] = []
    generated_configs = ["ruff.toml"]

    def __init__(self) -> None:
        pass

    def generate(self, registry, project_dir):  # type: ignore[override]
        return {}


class _DirPlugin(BaseLanguagePlugin):
    """Plugin that detects by directory presence."""

    key = "lua"
    name = "Lua"
    detect_files: list[str] = []
    detect_patterns = ["*.lua"]
    detect_dirs = ["lua"]
    copy_files: list[str] = []
    generated_configs = ["stylua.toml"]

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
# hook_config() default
# ---------------------------------------------------------------------------


def test_hook_config_returns_empty_dict_by_default() -> None:
    plugin = _PythonLike()
    assert plugin.hook_config() == {}


# ---------------------------------------------------------------------------
# check() default
# ---------------------------------------------------------------------------


def test_check_returns_empty_list_by_default(tmp_path: Path) -> None:
    from ai_guardrails.models.registry import ExceptionRegistry

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
