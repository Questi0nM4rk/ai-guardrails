"""RustPlugin — detects Rust projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class RustPlugin(BaseLanguagePlugin):
    """Language plugin for Rust projects."""

    key = "rust"
    name = "Rust"
    detect_files = ["Cargo.toml"]
    detect_patterns = ["*.rs"]
    detect_dirs: list[str] = []
    copy_files = ["rustfmt.toml"]
    generated_configs: list[str] = []

    _HOOKS_YAML = """\
pre-commit:
  commands:
    rust-format-and-stage:
      glob: "*.rs"
      run: cargo fmt --all && git add {staged_files}
      stage_fixed: true
      priority: 1
    cargo-clippy:
      glob: "*.rs"
      run: cargo clippy --all-targets --all-features -- -D warnings -D clippy::pedantic -D clippy::nursery -A clippy::module_name_repetitions
      priority: 2
    cargo-audit:
      run: cargo audit --deny warnings
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        return yaml.safe_load(self._HOOKS_YAML) or {}
