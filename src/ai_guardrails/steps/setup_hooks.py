"""SetupHooksStep — activates lefthook hooks after config generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext

_LEFTHOOK_NOT_FOUND_MSG = (
    "lefthook install failed: lefthook not found"
    " — install with: brew install lefthook"
    "  OR  go install github.com/evilmartians/lefthook@latest"
)


class SetupHooksStep:
    """Runs `lefthook install` to activate git hooks in the project."""

    name = "setup-hooks"

    def validate(self, _ctx: PipelineContext) -> list[str]:
        """No preconditions — lefthook may or may not be installed."""
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Run `lefthook install` in the project directory."""
        try:
            result = ctx.command_runner.run(
                ["lefthook", "install"],
                cwd=ctx.project_dir,
            )
        except FileNotFoundError:
            return StepResult(status="warn", message=_LEFTHOOK_NOT_FOUND_MSG)
        if result.returncode != 0:
            return StepResult(
                status="warn",
                message=f"lefthook install failed: {result.stderr}",
            )
        return StepResult(status="ok", message="Hooks installed (lefthook install)")
