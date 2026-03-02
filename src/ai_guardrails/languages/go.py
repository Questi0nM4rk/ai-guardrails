"""GoPlugin — detects Go projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class GoPlugin(BaseLanguagePlugin):
    """Language plugin for Go projects."""

    key = "go"
    name = "Go"
    detect_files = ["go.mod", "go.sum"]
    detect_patterns = ["*.go"]
    detect_dirs: list[str] = []
    copy_files: list[str] = []
    generated_configs: list[str] = []

    _HOOKS_YAML = """\
pre-commit:
  commands:
    go-format-and-stage:
      glob: "*.go"
      run: gofmt -w {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    go-vet:
      glob: "*.go"
      run: go vet ./...
      priority: 2
    staticcheck:
      glob: "*.go"
      run: staticcheck ./...
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
