"""SetupCIStep — copies CI workflow template to .github/workflows/check.yml."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext

_CI_OUTPUT = Path(".github/workflows/check.yml")


class SetupCIStep:
    """Copies CI workflow template to project. Skips if exists (unless force)."""

    name = "setup-ci"

    def __init__(self, template_path: Path) -> None:
        self._template = template_path

    def validate(self, _ctx: PipelineContext) -> list[str]:
        if not self._template.exists():
            return [f"CI workflow template not found: {self._template}"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        target = ctx.project_dir / _CI_OUTPUT
        if ctx.file_manager.exists(target) and not ctx.force:
            return StepResult(
                status="skip",
                message=f"{_CI_OUTPUT} already exists (use --force to overwrite)",
            )
        content = self._template.read_text()
        with contextlib.suppress(FileExistsError, AttributeError):
            ctx.file_manager.mkdir(target.parent, parents=True, exist_ok=True)
        ctx.file_manager.write_text(target, content)
        return StepResult(status="ok", message=f"Created {_CI_OUTPUT}")
