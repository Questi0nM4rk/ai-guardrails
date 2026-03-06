"""StatusPipeline — shows project health.

Steps: DetectLanguages → LoadRegistry → StatusStep
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.languages._registry import discover_plugins
from ai_guardrails.pipelines.base import Pipeline, PipelineContext
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.load_registry import LoadRegistryStep
from ai_guardrails.steps.status_step import StatusStep

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.pipelines.base import StepResult


class StatusPipeline:
    """Orchestrates project health reporting."""

    def __init__(
        self,
        data_dir: Path,
        custom_plugins_dir: Path | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._custom_plugins_dir = custom_plugins_dir

    def run(
        self,
        project_dir: Path,
        file_manager: FileManager,
        command_runner: CommandRunner,
        config_loader: ConfigLoader,
        console: Console,
    ) -> list[StepResult]:
        plugins = discover_plugins(self._data_dir, custom_dir=self._custom_plugins_dir)
        ctx = PipelineContext(
            project_dir=project_dir,
            file_manager=file_manager,
            command_runner=command_runner,
            config_loader=config_loader,
            console=console,
            languages=[],
            registry=None,
            dry_run=False,
            force=False,
        )

        steps: list = [
            DetectLanguagesStep(plugins=plugins),
            LoadRegistryStep(),
            StatusStep(),
        ]

        pipeline = Pipeline(steps=steps)
        return pipeline.run(ctx)
