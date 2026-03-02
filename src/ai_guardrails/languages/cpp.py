"""CppPlugin — detects C/C++ projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class CppPlugin(BaseLanguagePlugin):
    """Language plugin for C/C++ projects."""

    key = "cpp"
    name = "C/C++"
    detect_files = ["CMakeLists.txt"]
    detect_patterns = ["*.cpp", "*.c", "*.h", "*.hpp"]
    detect_dirs: list[str] = []
    copy_files = [".clang-format", ".clang-tidy"]
    generated_configs: list[str] = []

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
