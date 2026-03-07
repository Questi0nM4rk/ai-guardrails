"""LuaPlugin — detects Lua projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

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

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"
