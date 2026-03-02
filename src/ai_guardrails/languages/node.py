"""NodePlugin — detects TypeScript/JavaScript projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class NodePlugin(BaseLanguagePlugin):
    """Language plugin for TypeScript/JavaScript projects."""

    key = "node"
    name = "TypeScript/JavaScript"
    detect_files = ["package.json", "tsconfig.json"]
    detect_patterns = ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs"]
    detect_dirs: list[str] = []
    copy_files = ["biome.json"]
    generated_configs: list[str] = []

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
