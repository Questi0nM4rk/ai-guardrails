"""DotnetPlugin — detects C#/.NET projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path


class DotnetPlugin(BaseLanguagePlugin):
    """Language plugin for C#/.NET projects."""

    key = "dotnet"
    name = "C#/.NET"
    detect_files: ClassVar[list[str]] = []
    detect_patterns: ClassVar[list[str]] = ["*.csproj", "*.sln", "*.slnx"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = ["Directory.Build.props", ".globalconfig"]
    generated_configs: ClassVar[list[str]] = []

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

    def hook_config(self) -> dict[str, object]:
        return yaml.safe_load(self._HOOKS_YAML) or {}
