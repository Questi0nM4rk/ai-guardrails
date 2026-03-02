"""GenerateConfigsStep — runs all applicable generators to produce config files.

Receives a list of Generator instances. Each generator.generate() returns
{relative_path: content}. The step writes all outputs via FileManager.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Protocol

from ai_guardrails.pipelines.base import PipelineContext, StepResult

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry


class _GeneratorProtocol(Protocol):
    name: str
    output_files: list[str]

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]: ...


class GenerateConfigsStep:
    """Runs all generators and writes their output files."""

    name = "generate-configs"

    def __init__(self, generators: list[_GeneratorProtocol]) -> None:
        self._generators = generators

    def validate(self, ctx: PipelineContext) -> list[str]:
        if ctx.registry is None:
            return ["Registry not loaded — run scaffold-registry first"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        assert ctx.registry is not None  # guaranteed by validate()
        lang_keys = [lang.key for lang in ctx.languages]
        generated: list[str] = []

        for gen in self._generators:
            outputs = gen.generate(ctx.registry, lang_keys, ctx.project_dir)
            for path, content in outputs.items():
                # Ensure parent dir exists in FakeFileManager context
                # (FakeFileManager doesn't need mkdir, real FileManager does)
                with contextlib.suppress(FileExistsError, AttributeError):
                    ctx.file_manager.mkdir(path.parent, parents=True, exist_ok=True)
                ctx.file_manager.write_text(path, content)
                generated.append(path.name)

        if not generated:
            return StepResult(status="ok", message="No configs generated")
        return StepResult(status="ok", message=f"Generated: {', '.join(generated)}")
