"""ShellPlugin — detects Shell script projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path


class ShellPlugin(BaseLanguagePlugin):
    """Language plugin for Shell projects."""

    key = "shell"
    name = "Shell"
    detect_files: ClassVar[list[str]] = []
    detect_patterns: ClassVar[list[str]] = ["*.sh", "*.bash"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = []

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"
