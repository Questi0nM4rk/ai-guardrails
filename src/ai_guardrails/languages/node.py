"""NodePlugin — detects TypeScript/JavaScript projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path


class NodePlugin(BaseLanguagePlugin):
    """Language plugin for TypeScript/JavaScript projects."""

    key = "node"
    name = "TypeScript/JavaScript"
    detect_files: ClassVar[list[str]] = ["package.json", "tsconfig.json"]
    detect_patterns: ClassVar[list[str]] = [
        "*.js",
        "*.jsx",
        "*.ts",
        "*.tsx",
        "*.mjs",
        "*.cjs",
    ]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = ["biome.json"]
    generated_configs: ClassVar[list[str]] = []

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"
