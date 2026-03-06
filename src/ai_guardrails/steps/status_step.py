"""StatusStep — prints project health: languages, configs, hooks.

Always returns StepResult(status="ok") — informational only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext


class StatusStep:
    """Prints project health status to console. Never fails the pipeline."""

    name = "status"

    def validate(self, ctx: PipelineContext) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        self._print_languages(ctx)
        self._print_exceptions(ctx)
        self._print_configs(ctx)
        self._print_hooks(ctx)
        return StepResult(status="ok", message="Status complete")

    def _print_languages(self, ctx: PipelineContext) -> None:
        if ctx.languages:
            lang_names = ", ".join(p.key for p in ctx.languages)
            ctx.console.info(f"Languages detected:  {lang_names}")
        else:
            ctx.console.info("Languages detected:  (none)")

    def _print_exceptions(self, ctx: PipelineContext) -> None:
        if ctx.registry is None:
            ctx.console.info("Exceptions:          (registry not loaded)")
            return
        total = len(ctx.registry.exceptions) + len(ctx.registry.file_exceptions)
        ctx.console.info(
            f"Exceptions:          {total} rules in .guardrails-exceptions.toml"
        )

    def _print_configs(self, ctx: PipelineContext) -> None:
        if not ctx.languages or ctx.registry is None:
            ctx.console.info("Configs:             (no languages detected)")
            return

        ctx.console.info("Configs:")
        for plugin in ctx.languages:
            issues = plugin.check(ctx.registry, ctx.project_dir)
            for filename in plugin.generated_configs:
                if issues:
                    ctx.console.warning(
                        f"  {filename:<24} STALE — run: ai-guardrails generate"
                    )
                else:
                    ctx.console.info(f"  {filename:<24} fresh")

    def _print_hooks(self, ctx: PipelineContext) -> None:
        result = ctx.command_runner.run(["lefthook", "version"])
        if result.returncode == 0:
            version = result.stdout.strip() or "lefthook"
            ctx.console.info(f"Hooks:               installed ({version})")
        else:
            ctx.console.warning(
                "Hooks:               NOT installed — run: lefthook install"
            )
