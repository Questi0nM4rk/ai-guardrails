"""Pipeline framework — PipelineContext, StepResult, PipelineStep Protocol, Pipeline runner.

All steps receive PipelineContext for dependency injection.
Pipeline stops on error; continues on warn and skip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.infra.command_runner import CommandRunner
    from ai_guardrails.infra.config_loader import ConfigLoader
    from ai_guardrails.infra.console import Console
    from ai_guardrails.infra.file_manager import FileManager
    from ai_guardrails.models.language import LanguageConfig
    from ai_guardrails.models.registry import ExceptionRegistry


@dataclass
class StepResult:
    """Result from a single pipeline step execution."""

    status: Literal["ok", "skip", "warn", "error"]
    message: str


@dataclass
class PipelineContext:
    """Shared context passed to every pipeline step."""

    project_dir: Path
    file_manager: FileManager
    command_runner: CommandRunner
    config_loader: ConfigLoader
    console: Console
    languages: list[LanguageConfig]
    registry: ExceptionRegistry | None
    dry_run: bool
    force: bool


@runtime_checkable
class PipelineStep(Protocol):
    """Protocol for pipeline steps."""

    name: str

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Return list of validation errors (empty = ok to proceed)."""
        ...

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Execute the step and return a result."""
        ...


class Pipeline:
    """Runs a sequence of PipelineSteps, stopping on error."""

    def __init__(self, steps: list[PipelineStep]) -> None:
        self._steps = steps

    def run(self, ctx: PipelineContext) -> list[StepResult]:
        """Execute steps in order. Stop on first error."""
        results: list[StepResult] = []
        for step in self._steps:
            errors = step.validate(ctx)
            if errors:
                results.append(StepResult(status="error", message="; ".join(errors)))
                break
            result = step.execute(ctx)
            results.append(result)
            if result.status == "error":
                break
        return results

    def succeeded(self, results: list[StepResult]) -> bool:
        """Return True if all results are ok, skip, or warn."""
        return all(r.status in ("ok", "skip", "warn") for r in results)
