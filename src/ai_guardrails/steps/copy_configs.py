"""CopyConfigsStep — copies language-specific base configs to project.

Handles configs that don't go through generators (rustfmt.toml, .clang-format,
stylua.toml, .clang-tidy, Directory.Build.props, .globalconfig).
Skips existing files unless force=True.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import PipelineContext, StepResult

if TYPE_CHECKING:
    from pathlib import Path


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

                ctx.file_manager.copy(src, dst)
                copied.append(config_file)

        if not copied and skipped:
            return StepResult(
                status="skip",
                message=f"All configs exist (use --force to overwrite): {', '.join(skipped)}",
            )

        parts = []
        if copied:
            parts.append(f"Copied: {', '.join(copied)}")
        if skipped:
            parts.append(f"Skipped (exists): {', '.join(skipped)}")

        return StepResult(
            status="ok", message="; ".join(parts) if parts else "No configs to copy"
        )
