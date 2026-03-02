"""LuaPlugin — detects Lua projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class LuaPlugin(BaseLanguagePlugin):
    """Language plugin for Lua projects."""

    key = "lua"
    name = "Lua"
    detect_files: list[str] = []
    detect_patterns = ["*.rockspec", "*.lua"]
    detect_dirs = ["lua"]
    copy_files = ["stylua.toml"]
    generated_configs: list[str] = []

    _HOOKS_YAML = """\
pre-commit:
  commands:
    lua-format-and-stage:
      glob: "*.lua"
      run: stylua {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    luacheck:
      glob: "*.lua"
      run: luacheck {staged_files}
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
