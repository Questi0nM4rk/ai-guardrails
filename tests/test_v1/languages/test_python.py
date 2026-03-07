"""Tests for PythonPlugin — detects Python, generates ruff.toml."""

from __future__ import annotations

import tomllib  # type: ignore[no-redef]
from typing import TYPE_CHECKING

import tomli_w

from ai_guardrails.generators.base import HASH_HEADER_PREFIX
from ai_guardrails.languages.python import PythonPlugin
from ai_guardrails.models.registry import ExceptionRegistry

if TYPE_CHECKING:
    from pathlib import Path


def _make_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    configs_dir = data_dir / "configs"
    configs_dir.mkdir(parents=True)
    base_config = {
        "target-version": "py311",
        "line-length": 88,
        "lint": {
            "select": ["ALL"],
            "ignore": ["W191", "COM812"],
            "per-file-ignores": {
                "tests/**/*.py": ["ARG001", "PLR2004"],
            },
        },
    }
    with (configs_dir / "ruff.toml").open("wb") as f:
        tomli_w.dump(base_config, f)
    return data_dir


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


def _registry_with_ruff_ignores(rules: list[str]) -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {"ruff": {"ignore": rules}},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


# ---------------------------------------------------------------------------
# Plugin attributes
# ---------------------------------------------------------------------------


def test_python_plugin_key(tmp_path: Path) -> None:
    plugin = PythonPlugin(tmp_path)
    assert plugin.key == "python"


def test_python_plugin_name(tmp_path: Path) -> None:
    plugin = PythonPlugin(tmp_path)
    assert plugin.name == "Python"


def test_python_plugin_generated_configs(tmp_path: Path) -> None:
    plugin = PythonPlugin(tmp_path)
    assert "ruff.toml" in plugin.generated_configs


def test_python_plugin_copy_files_empty(tmp_path: Path) -> None:
    plugin = PythonPlugin(tmp_path)
    assert plugin.copy_files == []


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------


def test_python_detect_by_pyproject_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_python_detect_by_setup_py(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text("from setuptools import setup\n")
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_python_detect_by_requirements_txt(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests\n")
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_python_detect_by_py_file(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_python_detect_false_for_go_project(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/foo\n")
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is False


def test_python_detect_false_for_empty_dir(tmp_path: Path) -> None:
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is False


def test_python_detect_skips_venv_py_files(tmp_path: Path) -> None:
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "lib.py").write_text("# vendored\n")
    plugin = PythonPlugin(tmp_path)
    assert plugin.detect(tmp_path) is False


# ---------------------------------------------------------------------------
# generate() — ruff.toml
# ---------------------------------------------------------------------------


def test_generate_produces_ruff_toml(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    assert project_dir / "ruff.toml" in outputs


def test_generate_ruff_toml_has_hash_header(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / "ruff.toml"]
    assert content.startswith(HASH_HEADER_PREFIX)


def test_generate_ruff_toml_preserves_base_config(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outputs = plugin.generate(_empty_registry(), project_dir)
    content = outputs[project_dir / "ruff.toml"]
    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    assert parsed["target-version"] == "py311"
    assert parsed["line-length"] == 88


def test_generate_ruff_toml_merges_registry_ignores(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _registry_with_ruff_ignores(["E501", "W503"])
    outputs = plugin.generate(registry, project_dir)
    content = outputs[project_dir / "ruff.toml"]
    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    ignores = parsed["lint"]["ignore"]
    assert "W191" in ignores  # base
    assert "E501" in ignores  # registry
    assert "W503" in ignores  # registry


def test_generate_ruff_toml_ignores_are_sorted(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _registry_with_ruff_ignores(["Z999", "A001"])
    outputs = plugin.generate(registry, project_dir)
    content = outputs[project_dir / "ruff.toml"]
    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    ignores = parsed["lint"]["ignore"]
    assert ignores == sorted(ignores)


# ---------------------------------------------------------------------------
# hook_config()
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_python_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    registry = _empty_registry()
    outputs = plugin.generate(registry, project_dir)
    for path, content in outputs.items():
        path.write_text(content)
    assert plugin.check(registry, project_dir) == []


def test_python_check_reports_missing_ruff_toml(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    issues = plugin.check(_empty_registry(), project_dir)
    assert any("ruff.toml" in i for i in issues)


def test_build_config_custom_overrides_dont_destroy_registry_ignores(
    tmp_path: Path,
) -> None:
    """Custom overrides via registry.custom['ruff'] must not replace registry ignores.

    Regression test for M-3: deep_merge treats lists as scalars and replaces
    the ignore array built from registry.get_ignores().  After the fix, custom
    overrides are applied BEFORE the registry ignore merge, so registry ignores
    always win.
    """
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Registry with BOTH custom ruff overrides AND global ignores
    registry = ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {"ruff": {"ignore": ["F401", "F811"]}},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {"ruff": {"lint": {"ignore": ["E501"]}}},
            "inline_suppressions": [],
        }
    )

    outputs = plugin.generate(registry, project_dir)
    content = outputs[project_dir / "ruff.toml"]
    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    ignores = parsed["lint"]["ignore"]

    # Base config ignores (W191, COM812) must be present
    assert "W191" in ignores, f"base ignore W191 missing from {ignores}"
    assert "COM812" in ignores, f"base ignore COM812 missing from {ignores}"
    # Custom override ignore (E501) must be present
    assert "E501" in ignores, f"custom ignore E501 missing from {ignores}"
    # Registry global ignores (F401, F811) must ALWAYS be present
    assert "F401" in ignores, f"registry ignore F401 missing from {ignores}"
    assert "F811" in ignores, f"registry ignore F811 missing from {ignores}"


def test_python_check_reports_stale_ruff_toml(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = PythonPlugin(data_dir)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # Generate with empty registry
    outputs = plugin.generate(_empty_registry(), project_dir)
    for path, content in outputs.items():
        path.write_text(content)
    # Check with different registry
    registry_v2 = _registry_with_ruff_ignores(["E501"])
    issues = plugin.check(registry_v2, project_dir)
    assert any("ruff.toml" in i for i in issues)
