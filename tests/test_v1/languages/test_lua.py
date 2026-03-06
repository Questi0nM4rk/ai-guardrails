"""Tests for LuaPlugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages.lua import LuaPlugin
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


def test_lua_plugin_key(tmp_path: Path) -> None:
    assert LuaPlugin(tmp_path).key == "lua"


def test_lua_plugin_name(tmp_path: Path) -> None:
    assert LuaPlugin(tmp_path).name == "Lua"


def test_lua_detect_by_lua_file(tmp_path: Path) -> None:
    (tmp_path / "init.lua").write_text("-- lua\n")
    assert LuaPlugin(tmp_path).detect(tmp_path) is True


def test_lua_detect_by_lua_dir(tmp_path: Path) -> None:
    (tmp_path / "lua").mkdir()
    assert LuaPlugin(tmp_path).detect(tmp_path) is True


def test_lua_detect_false_for_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert LuaPlugin(tmp_path).detect(tmp_path) is False


def test_lua_copy_files_includes_stylua(tmp_path: Path) -> None:
    assert "stylua.toml" in LuaPlugin(tmp_path).copy_files


def test_lua_hook_config_has_format_command(tmp_path: Path) -> None:
    config = LuaPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "lua-format-and-stage" in commands


def test_lua_hook_config_has_luacheck(tmp_path: Path) -> None:
    config = LuaPlugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "luacheck" in commands


def test_lua_generate_returns_empty(tmp_path: Path) -> None:
    outputs = LuaPlugin(tmp_path).generate(_empty_registry(), tmp_path)
    assert outputs == {}
