"""DetectLanguagesStep — detects languages present in the project directory.

Uses LanguagePlugin.detect() for each registered plugin.
Updates ctx.languages in-place with the list of active plugins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import PipelineContext, StepResult

if TYPE_CHECKING:
    from ai_guardrails.languages._base import LanguagePlugin


class DetectLanguagesStep:
    """Runs detect() on each plugin and populates ctx.languages."""

    name = "detect-languages"

    def __init__(self, plugins: list[LanguagePlugin]) -> None:
        self._plugins = plugins

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        detected = [p for p in self._plugins if p.detect(ctx.project_dir)]
        ctx.languages = detected

        if not detected:
            return StepResult(
                status="warn",
                message="No languages detected — check your project structure",
            )
        names = ", ".join(p.name for p in detected)
        return StepResult(status="ok", message=f"Detected: {names}")
