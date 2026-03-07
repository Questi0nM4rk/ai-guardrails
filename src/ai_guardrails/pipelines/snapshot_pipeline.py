"""SnapshotPipeline — capture current lint issues as baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.languages._registry import discover_plugins
from ai_guardrails.pipelines.base import Pipeline, PipelineContext
from ai_guardrails.steps.detect_languages import DetectLanguagesStep
from ai_guardrails.steps.snapshot_step import SnapshotStep

if TYPE_CHECKING:
    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.pipelines.base import StepResult

_DEFAULT_BASELINE = Path(".guardrails-baseline.json")


@dataclass
class SnapshotOptions:
    """Options for the snapshot command."""

    baseline_file: Path | None = None
    dry_run: bool = False


class SnapshotPipeline:
    """Orchestrates lint issue collection and baseline file creation."""

    def __init__(
        self,
        options: SnapshotOptions,
        data_dir: Path,
        custom_plugins_dir: Path | None = None,
    ) -> None:
        self._options = options
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
        baseline = (
            self._options.baseline_file
            if self._options.baseline_file is not None
            else project_dir / _DEFAULT_BASELINE
        )

        ctx = PipelineContext(
            project_dir=project_dir,
            file_manager=file_manager,
            command_runner=command_runner,
            config_loader=config_loader,
            console=console,
            languages=[],
            registry=None,
            dry_run=self._options.dry_run,
            force=False,
        )

        plugins = discover_plugins(self._data_dir, custom_dir=self._custom_plugins_dir)
        steps = [
            DetectLanguagesStep(plugins=plugins),
            SnapshotStep(baseline_file=baseline, dry_run=self._options.dry_run),
        ]

        return Pipeline(steps=steps).run(ctx)
