"""ReportPipeline — show audit log summary."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import Pipeline, PipelineContext
from ai_guardrails.steps.report_step import ReportStep

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.pipelines.base import StepResult


class ReportPipeline:
    """Displays audit log summary."""

    def run(
        self,
        project_dir: Path,
        file_manager: FileManager,
        command_runner: CommandRunner,
        config_loader: ConfigLoader,
        console: Console,
    ) -> list[StepResult]:
        """Execute ReportStep within a pipeline context."""
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
        pipeline = Pipeline(steps=[ReportStep()])
        return pipeline.run(ctx)
