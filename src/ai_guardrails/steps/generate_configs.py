"""GenerateConfigsStep — runs all active language plugins to produce config files.

For each active plugin, calls plugin.generate() to get {path: content} pairs.
Standalone Generator objects (ruff, markdownlint, editorconfig, lefthook)
run after plugins and have final say over their owned files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators import DEFAULT_GENERATORS
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.generators.base import Generator
    from ai_guardrails.pipelines.base import PipelineContext


class GenerateConfigsStep:
    """Runs all active plugins and writes their generated config files."""

    name = "generate-configs"

    def __init__(
        self,
        generators: list[Generator] | None = None,
    ) -> None:
        self.generators: list[Generator] = (
            generators if generators is not None else list(DEFAULT_GENERATORS)
        )
        self._gen_owned: set[str] = {
            f for gen in self.generators for f in gen.output_files
        }

    def validate(self, ctx: PipelineContext) -> list[str]:
        if ctx.registry is None:
            if ctx.dry_run:
                return []  # execute() will skip gracefully
            return ["Registry not loaded — run scaffold-registry first"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        if ctx.registry is None:
            return StepResult(status="skip", message="Dry-run: registry not loaded")
        if ctx.check:
            return self._run_check(ctx)
        return self._run_generate(ctx)

    def _run_check(self, ctx: PipelineContext) -> StepResult:
        """Check mode: call plugin.check() and report issues without writing."""
        if ctx.registry is None:
            raise RuntimeError("registry must be loaded before generate-configs")

        all_issues: list[str] = []
        for plugin in ctx.languages:
            if not any(f in self._gen_owned for f in plugin.generated_configs):
                all_issues.extend(plugin.check(ctx.registry, ctx.project_dir))

        # Check standalone generators
        lang_keys = [p.key for p in ctx.languages]
        for gen in self.generators:
            all_issues.extend(gen.check(ctx.registry, ctx.project_dir, lang_keys))

        if all_issues:
            for issue in all_issues:
                ctx.console.error(issue)
            return StepResult(
                status="error",
                message=f"{len(all_issues)} config(s) stale or tampered",
            )
        return StepResult(status="ok", message="All configs are fresh")

    def _run_generate(self, ctx: PipelineContext) -> StepResult:
        """Generate mode: call plugin.generate() and write config files."""
        if ctx.registry is None:
            raise RuntimeError("registry must be loaded before generate-configs")
        generated: list[str] = []

        # 1. Generate per-plugin config files (language plugins)
        for plugin in ctx.languages:
            outputs = plugin.generate(ctx.registry, ctx.project_dir)
            for path, content in outputs.items():
                if path.name in self._gen_owned:
                    continue  # standalone generator has final say
                ctx.file_manager.mkdir(path.parent, parents=True, exist_ok=True)
                ctx.file_manager.write_text(path, content)
                generated.append(path.name)

        # 2. Run standalone generators (ruff, markdownlint, editorconfig, lefthook)
        lang_keys = [p.key for p in ctx.languages]
        for gen in self.generators:
            outputs = gen.generate(ctx.registry, lang_keys, ctx.project_dir)
            for path, content in outputs.items():
                abs_path = ctx.project_dir / path
                ctx.file_manager.mkdir(abs_path.parent, parents=True, exist_ok=True)
                ctx.file_manager.write_text(abs_path, content)
                generated.append(path.name)

        if not generated:
            return StepResult(status="ok", message="No configs generated")
        return StepResult(status="ok", message=f"Generated: {', '.join(generated)}")
