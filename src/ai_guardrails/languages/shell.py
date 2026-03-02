"""ShellPlugin — detects Shell script projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class ShellPlugin(BaseLanguagePlugin):
    """Language plugin for Shell projects."""

    key = "shell"
    name = "Shell"
    detect_files: list[str] = []
    detect_patterns = ["*.sh", "*.bash"]
    detect_dirs: list[str] = []
    copy_files: list[str] = []
    generated_configs: list[str] = []

    _HOOKS_YAML = """\
pre-commit:
  commands:
    shell-format-and-stage:
      glob: "*.{sh,bash,zsh}"
      run: shfmt -i 2 -ci -bn -w {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    shellcheck:
      glob: "*.{sh,bash,zsh}"
      run: shellcheck --severity=info -x {staged_files}
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
