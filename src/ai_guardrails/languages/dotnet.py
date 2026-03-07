"""DotnetPlugin — detects C#/.NET projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

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

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"
