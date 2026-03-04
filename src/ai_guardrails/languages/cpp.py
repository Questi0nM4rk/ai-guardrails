"""CppPlugin — detects C/C++ projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path


class CppPlugin(BaseLanguagePlugin):
    """Language plugin for C/C++ projects."""

    key = "cpp"
    name = "C/C++"
    detect_files: ClassVar[list[str]] = ["CMakeLists.txt"]
    detect_patterns: ClassVar[list[str]] = ["*.cpp", "*.c", "*.h", "*.hpp"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = [".clang-format", ".clang-tidy"]
    generated_configs: ClassVar[list[str]] = []

    _HOOKS_YAML = """\
pre-commit:
  commands:
    clang-format-and-stage:
      glob: "*.{c,h,cpp,hpp,cc,cxx,hxx}"
      run: clang-format -i {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    clang-tidy:
      glob: "*.{c,h,cpp,hpp,cc,cxx,hxx}"
      run: clang-tidy {staged_files} -- -Wall -Wextra
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
