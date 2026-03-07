"""Tests for NodePlugin — detects Node/TypeScript, generates biome.json."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages.node import NodePlugin
from ai_guardrails.models.registry import ExceptionRegistry

if TYPE_CHECKING:
    from pathlib import Path


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


def _make_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    configs_dir = data_dir / "configs"
    configs_dir.mkdir(parents=True)
    (configs_dir / "biome.json").write_text(
        '{"$schema": "https://biomejs.dev/schemas/1.4.1/schema.json"}\n'
    )
    return data_dir


def test_node_plugin_key(tmp_path: Path) -> None:
    plugin = NodePlugin(tmp_path)
    assert plugin.key == "node"


def test_node_plugin_name(tmp_path: Path) -> None:
    plugin = NodePlugin(tmp_path)
    assert plugin.name == "TypeScript/JavaScript"


def test_node_detect_by_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_node_detect_by_tsconfig(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}\n')
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_node_detect_by_ts_file(tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("const x = 1;\n")
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_node_detect_by_js_file(tmp_path: Path) -> None:
    (tmp_path / "index.js").write_text("console.log('hi');\n")
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is True


def test_node_detect_false_for_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is False


def test_node_detect_false_for_empty_dir(tmp_path: Path) -> None:
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is False


def test_node_detect_skips_node_modules(tmp_path: Path) -> None:
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.ts").write_text("// vendored\n")
    plugin = NodePlugin(tmp_path)
    assert plugin.detect(tmp_path) is False


def test_node_copy_files_includes_biome_json(tmp_path: Path) -> None:
    plugin = NodePlugin(tmp_path)
    assert "biome.json" in plugin.copy_files


def test_node_generated_configs_is_empty(tmp_path: Path) -> None:
    # biome.json is copied not generated
    plugin = NodePlugin(tmp_path)
    assert plugin.generated_configs == []


def test_node_generate_returns_empty(tmp_path: Path) -> None:
    """NodePlugin uses copy_files not generate()."""
    plugin = NodePlugin(tmp_path)
    outputs = plugin.generate(_empty_registry(), tmp_path)
    assert outputs == {}
