"""CopyConfigsStep — copies language-specific base configs to project.

Handles configs that don't go through generators (rustfmt.toml, .clang-format,
stylua.toml, .clang-tidy, Directory.Build.props, .globalconfig).
Prepends an ai-guardrails hash header so configs are tracked by the freshness
system. XML files (.props) are copied without a hash header.
Skips existing files unless force=True.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    JSONC_HASH_HEADER_PREFIX,
    compute_hash,
)
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.pipelines.base import PipelineContext

# File extensions that cannot carry a hash header (no single-line comment syntax)
_NO_HASH_EXTENSIONS = frozenset({".props", ".xml"})


def _hash_header_for(filename: str, body: str) -> str | None:
    """Return the hash header line for *filename*, or None to skip protection."""
    for ext in _NO_HASH_EXTENSIONS:
        if filename.endswith(ext):
            return None
    h = compute_hash(body)
    if filename.endswith(".json"):
        return f"{JSONC_HASH_HEADER_PREFIX}{h}"
    return f"{HASH_HEADER_PREFIX}{h}"


class CopyConfigsStep:
    """Copies language-specific base configs from package configs_dir to project."""

    name = "copy-configs"

    def __init__(self, configs_dir: Path) -> None:
        self._configs_dir = configs_dir

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        if not ctx.languages:
            return StepResult(
                status="skip", message="No languages detected — nothing to copy"
            )

        copied: list[str] = []
        skipped: list[str] = []

        for lang in ctx.languages:
            for config_file in lang.copy_files:
                src = self._configs_dir / config_file
                dst = ctx.project_dir / config_file

                if not ctx.file_manager.exists(src):
                    continue  # base config not in package — silently skip

                if ctx.file_manager.exists(dst) and not ctx.force:
                    skipped.append(config_file)
                    continue

                body = ctx.file_manager.read_text(src)
                header = _hash_header_for(config_file, body)
                content = f"{header}\n{body}" if header is not None else body
                ctx.file_manager.write_text(dst, content)
                copied.append(config_file)

        if not copied and skipped:
            names = ", ".join(skipped)
            return StepResult(
                status="skip",
                message=f"All configs exist (use --force to overwrite): {names}",
            )

        parts = []
        if copied:
            parts.append(f"Copied: {', '.join(copied)}")
        if skipped:
            parts.append(f"Skipped (exists): {', '.join(skipped)}")

        return StepResult(
            status="ok", message="; ".join(parts) if parts else "No configs to copy"
        )
