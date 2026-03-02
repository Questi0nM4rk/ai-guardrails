"""LoadRegistryStep — loads .guardrails-exceptions.toml into ctx.registry."""

from __future__ import annotations

import tomllib  # type: ignore[no-redef]

from ai_guardrails.constants import REGISTRY_FILENAME
from ai_guardrails.models.registry import ExceptionRegistry
from ai_guardrails.pipelines.base import PipelineContext, StepResult


class LoadRegistryStep:
    """Reads the exception registry from disk and sets ctx.registry."""

    name = "load-registry"

    def validate(self, ctx: PipelineContext) -> list[str]:
        registry_path = ctx.project_dir / REGISTRY_FILENAME
        if not ctx.file_manager.exists(registry_path):
            return [f"{REGISTRY_FILENAME} not found — run: ai-guardrails init"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        registry_path = ctx.project_dir / REGISTRY_FILENAME
        content = ctx.file_manager.read_text(registry_path)
        data = tomllib.loads(content)
        ctx.registry = ExceptionRegistry.from_toml(data)
        return StepResult(status="ok", message=f"Loaded {REGISTRY_FILENAME}")
