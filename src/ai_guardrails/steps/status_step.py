"""StatusStep — prints project health: languages, configs, hooks.

Always returns StepResult(status="ok") — informational only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators.editorconfig import EditorconfigGenerator
from ai_guardrails.generators.lefthook import LefthookGenerator
from ai_guardrails.generators.markdownlint import MarkdownlintGenerator
from ai_guardrails.generators.ruff import RuffGenerator
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.generators.base import Generator
    from ai_guardrails.pipelines.base import PipelineContext

_DEFAULT_GENERATORS: list[Generator] = [
    RuffGenerator(),
    MarkdownlintGenerator(),
    EditorconfigGenerator(),
    LefthookGenerator(),
]


class StatusStep:
    """Prints project health status to console. Never fails the pipeline."""

    name = "status"

    def __init__(self, generators: list[Generator] | None = None) -> None:
        self._generators: list[Generator] = (
            generators if generators is not None else list(_DEFAULT_GENERATORS)
        )
        self._gen_owned: set[str] = {
            f for gen in self._generators for f in gen.output_files
        }

    def validate(
        self,
        ctx: PipelineContext,  # ai-guardrails-allow: ARG002 "PipelineStep protocol"
    ) -> list[str]:
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
        if ctx.registry is None:
            ctx.console.info("Configs:             (registry not loaded)")
            return

        ctx.console.info("Configs:")
        lang_keys = [p.key for p in ctx.languages]

        # Generator-owned configs: each generator checks its own files.
        for gen in self._generators:
            issues = gen.check(ctx.registry, ctx.project_dir, lang_keys)
            for filename in gen.output_files:
                if issues:
                    ctx.console.warning(
                        f"  {filename:<24} STALE — run: ai-guardrails generate"
                    )
                else:
                    ctx.console.info(f"  {filename:<24} fresh")

        # Plugin-exclusive configs (not owned by any standalone generator).
        for plugin in ctx.languages:
            exclusive = [
                f for f in plugin.generated_configs if f not in self._gen_owned
            ]
            if not exclusive:
                continue
            issues = plugin.check(ctx.registry, ctx.project_dir)
            for filename in exclusive:
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
