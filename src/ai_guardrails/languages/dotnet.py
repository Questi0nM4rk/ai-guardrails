"""DotnetPlugin — detects C#/.NET projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class DotnetPlugin(BaseLanguagePlugin):
    """Language plugin for C#/.NET projects."""

    key = "dotnet"
    name = "C#/.NET"
    detect_files: list[str] = []
    detect_patterns = ["*.csproj", "*.sln", "*.slnx"]
    detect_dirs: list[str] = []
    copy_files = ["Directory.Build.props", ".globalconfig"]
    generated_configs: list[str] = []

    _HOOKS_YAML = """\
pre-commit:
  commands:
    dotnet-format-and-stage:
      glob: "*.{cs,csx,vb}"
      run: dotnet format --severity info && git add {staged_files}
      stage_fixed: true
      priority: 1
    dotnet-build:
      glob: "*.{cs,csx,vb,csproj,sln}"
      run: dotnet build --no-restore -warnaserror -c Release
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
