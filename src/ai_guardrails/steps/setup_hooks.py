"""SetupHooksStep — activates lefthook hooks after config generation."""

from __future__ import annotations

from ai_guardrails.pipelines.base import PipelineContext, StepResult


class SetupHooksStep:
    """Runs `lefthook install` to activate git hooks in the project."""

    name = "setup-hooks"

    def validate(self, ctx: PipelineContext) -> list[str]:
        """No preconditions — lefthook may or may not be installed."""
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Run `lefthook install` in the project directory."""
        result = ctx.command_runner.run(
            ["lefthook", "install"],
            cwd=ctx.project_dir,
        )
        if result.returncode != 0:
            return StepResult(
                status="warn",
                message=f"lefthook install failed: {result.stderr}",
            )
        return StepResult(status="ok", message="Hooks installed (lefthook install)")
