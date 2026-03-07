"""CheckPipeline — runs linters and compares against a baseline snapshot.

Steps: DetectLanguages → CheckStep

LoadRegistry is intentionally skipped: check does not need the exception
registry (it uses its own baseline file, not the exception allowlist).
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.languages._registry import discover_plugins
from ai_guardrails.pipelines.base import Pipeline, PipelineContext
from ai_guardrails.steps.check_step import CheckStep
from ai_guardrails.steps.detect_languages import DetectLanguagesStep

if TYPE_CHECKING:
    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.pipelines.base import StepResult

_DEFAULT_BASELINE = Path(".guardrails-baseline.json")


@dataclass
class CheckOptions:
    """Options for the check command."""

    baseline_file: Path | None = None


class CheckPipeline:
    """Orchestrates lint checking against a baseline snapshot."""

    def __init__(
        self,
        options: CheckOptions,
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
            dry_run=False,
            force=False,
        )

        plugins = discover_plugins(self._data_dir, custom_dir=self._custom_plugins_dir)
        steps = [
            DetectLanguagesStep(plugins=plugins),
            CheckStep(baseline_file=baseline),
        ]

        pipeline = Pipeline(steps=steps)
        results = pipeline.run(ctx)

        check_result = next(
            (r for r in results if r.status in ("ok", "error", "skip")), None
        )
        if check_result and check_result.status != "skip":
            status = "ok" if check_result.status == "ok" else "error"
            record = {
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "command": "check",
                "new_issues": sum(1 for r in results if r.status == "error"),
                "status": status,
            }
            audit_path = project_dir / ".guardrails-audit.jsonl"
            file_manager.append_text(audit_path, json.dumps(record) + "\n")

        return results
