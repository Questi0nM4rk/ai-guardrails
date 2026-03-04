"""ScaffoldRegistryStep — creates initial .guardrails-exceptions.toml.

Never overwrites existing registry — it is user data.
The force flag is intentionally ignored for this step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.constants import REGISTRY_FILENAME
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.pipelines.base import PipelineContext


class ScaffoldRegistryStep:
    """Creates .guardrails-exceptions.toml from template if not present."""

    name = "scaffold-registry"

    def __init__(self, template_path: Path) -> None:
        self._template = template_path

    def validate(self, _ctx: PipelineContext) -> list[str]:
        if not self._template.exists():
            return [f"Registry template not found: {self._template}"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        target = ctx.project_dir / REGISTRY_FILENAME
        if target.exists():
            return StepResult(
                status="skip",
                message=f"{REGISTRY_FILENAME} already exists (never overwritten)",
            )
        content = self._template.read_text()
        ctx.file_manager.write_text(target, content)
        return StepResult(status="ok", message=f"Created {REGISTRY_FILENAME}")
