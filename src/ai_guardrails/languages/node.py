"""NodePlugin — detects TypeScript/JavaScript projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import yaml

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

    _HOOKS_YAML = """\
pre-commit:
  commands:
    node-format-and-stage:
      glob: "*.{js,jsx,ts,tsx,mjs,cjs}"
      run: biome check --apply {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    biome-check:
      glob: "*.{js,jsx,ts,tsx,mjs,cjs}"
      run: biome check --error-on-warnings {staged_files}
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
