"""LuaPlugin — detects Lua projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path


class LuaPlugin(BaseLanguagePlugin):
    """Language plugin for Lua projects."""

    key = "lua"
    name = "Lua"
    detect_files: ClassVar[list[str]] = []
    detect_patterns: ClassVar[list[str]] = ["*.rockspec", "*.lua"]
    detect_dirs: ClassVar[list[str]] = ["lua"]
    copy_files: ClassVar[list[str]] = ["stylua.toml"]
    generated_configs: ClassVar[list[str]] = []

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
