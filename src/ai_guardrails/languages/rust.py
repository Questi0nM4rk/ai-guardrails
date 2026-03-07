"""RustPlugin — detects Rust projects."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path


class RustPlugin(BaseLanguagePlugin):
    """Language plugin for Rust projects."""

    key = "rust"
    name = "Rust"
    detect_files: ClassVar[list[str]] = ["Cargo.toml"]
    detect_patterns: ClassVar[list[str]] = ["*.rs"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = ["rustfmt.toml"]
    generated_configs: ClassVar[list[str]] = []

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"
