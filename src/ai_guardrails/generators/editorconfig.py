"""EditorconfigGenerator — pure copy of base .editorconfig.

No exception merge needed. The .editorconfig is identical across all projects.
Adds a hash header for tamper detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators.base import make_hash_header, verify_hash

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry


class EditorconfigGenerator:
    """Copies base .editorconfig into project root with a hash header."""

    name = "editorconfig"
    output_files = [".editorconfig"]

    def __init__(self, configs_dir: Path) -> None:
        self._configs_dir = configs_dir

    def _base_content(self) -> str:
        src = self._configs_dir / ".editorconfig"
        if not src.exists():
            raise FileNotFoundError(src)
        return src.read_text()

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/.editorconfig: content_with_hash_header}."""
        base = self._base_content()
        header = make_hash_header(base)
        full_content = f"{header}\n{base}"
        return {project_dir / ".editorconfig": full_content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if .editorconfig is missing or tampered."""
        target = project_dir / ".editorconfig"
        if not target.exists():
            return [".editorconfig is missing — run: ai-guardrails generate"]
        try:
            base = self._base_content()
        except FileNotFoundError:
            return [".editorconfig base config not found in package data"]
        existing = target.read_text()
        if not verify_hash(existing, base):
            return [".editorconfig has been tampered with — run: ai-guardrails generate"]
        return []
