"""Tests for discover_plugins — core plugin loading and custom dir scanning."""

from __future__ import annotations

import textwrap
from pathlib import Path

from ai_guardrails.languages._registry import _load_custom_plugins, discover_plugins


def _make_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    configs_dir = data_dir / "configs"
    configs_dir.mkdir(parents=True)
    (configs_dir / ".editorconfig").write_text("[*]\nend_of_line = lf\n")
    (configs_dir / ".markdownlint.jsonc").write_text('{"default": true}\n')
    return data_dir


# ---------------------------------------------------------------------------
# Core plugins
# ---------------------------------------------------------------------------


def test_discover_plugins_returns_list(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir)
    assert isinstance(plugins, list)
    assert len(plugins) > 0


def test_discover_plugins_includes_universal(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir)
    keys = [p.key for p in plugins]
    assert "universal" in keys


def test_discover_plugins_includes_python(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir)
    keys = [p.key for p in plugins]
    assert "python" in keys


def test_discover_plugins_includes_all_core_languages(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir)
    keys = [p.key for p in plugins]
    expected_keys = [
        "universal",
        "python",
        "node",
        "rust",
        "go",
        "dotnet",
        "cpp",
        "lua",
        "shell",
    ]
    for expected_key in expected_keys:
        assert expected_key in keys, f"Missing plugin: {expected_key}"


def test_universal_is_first(tmp_path: Path) -> None:
    """UniversalPlugin must come first so it's always included."""
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir)
    assert plugins[0].key == "universal"


def test_discover_plugins_no_custom_dir(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir, custom_dir=None)
    assert len(plugins) == 9  # all core plugins


def test_discover_plugins_nonexistent_custom_dir(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugins = discover_plugins(data_dir, custom_dir=tmp_path / "nonexistent")
    assert len(plugins) == 9  # only core plugins, no error


# ---------------------------------------------------------------------------
# Custom dir loading
# ---------------------------------------------------------------------------


def test_discover_plugins_loads_custom_plugin(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    custom_dir = tmp_path / "plugins"
    custom_dir.mkdir()

    (custom_dir / "fortran.py").write_text(
        """\
from __future__ import annotations
from pathlib import Path
from ai_guardrails.languages._base import BaseLanguagePlugin

class FortranPlugin(BaseLanguagePlugin):
    key = "fortran"
    name = "Fortran"
    detect_files = ["*.f90"]
    copy_files: list[str] = []
    generated_configs: list[str] = []

    def __init__(self, data_dir: Path) -> None:
        pass
"""
    )

    plugins = discover_plugins(data_dir, custom_dir=custom_dir)
    keys = [p.key for p in plugins]
    assert "fortran" in keys


def test_discover_plugins_skips_underscore_files(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    custom_dir = tmp_path / "plugins"
    custom_dir.mkdir()

    (custom_dir / "_private.py").write_text(
        """\
from __future__ import annotations
from pathlib import Path
from ai_guardrails.languages._base import BaseLanguagePlugin

class PrivatePlugin(BaseLanguagePlugin):
    key = "private"
    name = "Private"
    copy_files: list[str] = []
    generated_configs: list[str] = []

    def __init__(self, data_dir: Path) -> None:
        pass
"""
    )

    plugins = discover_plugins(data_dir, custom_dir=custom_dir)
    keys = [p.key for p in plugins]
    assert "private" not in keys


def test_discover_plugins_custom_plugin_satisfies_protocol(tmp_path: Path) -> None:
    from ai_guardrails.languages._base import LanguagePlugin

    data_dir = _make_data_dir(tmp_path)
    custom_dir = tmp_path / "plugins"
    custom_dir.mkdir()

    (custom_dir / "kotlin.py").write_text(
        """\
from __future__ import annotations
from pathlib import Path
from ai_guardrails.languages._base import BaseLanguagePlugin

class KotlinPlugin(BaseLanguagePlugin):
    key = "kotlin"
    name = "Kotlin"
    detect_patterns = ["*.kt"]
    copy_files: list[str] = []
    generated_configs: list[str] = []

    def __init__(self, data_dir: Path) -> None:
        pass
"""
    )

    plugins = discover_plugins(data_dir, custom_dir=custom_dir)
    kotlin = next(p for p in plugins if p.key == "kotlin")
    assert isinstance(kotlin, LanguagePlugin)


# ---------------------------------------------------------------------------
# L-8: _load_custom_plugins error paths
# ---------------------------------------------------------------------------


def test_load_custom_plugins_handles_syntax_error(tmp_path: Path) -> None:
    """Malformed plugin file is skipped with warning."""
    plugin_file = tmp_path / "bad_plugin.py"
    plugin_file.write_text("def broken(\n")  # syntax error
    result = _load_custom_plugins(tmp_path, tmp_path)
    assert result == []


def test_load_custom_plugins_handles_init_failure(tmp_path: Path) -> None:
    """Plugin that raises in __init__ is skipped."""
    plugin_file = tmp_path / "crash_plugin.py"
    plugin_file.write_text(
        textwrap.dedent("""\
        from ai_guardrails.languages._base import BaseLanguagePlugin
        class CrashPlugin(BaseLanguagePlugin):
            key = "crash"
            name = "Crash"
            detect_files = []
            detect_patterns = []
            detect_dirs = []
            copy_files = []
            generated_configs = []
            def __init__(self, data_dir):
                raise RuntimeError("boom")
    """)
    )
    result = _load_custom_plugins(tmp_path, tmp_path)
    assert result == []
