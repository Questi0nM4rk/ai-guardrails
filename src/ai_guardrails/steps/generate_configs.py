"""GenerateConfigsStep — runs all active language plugins to produce config files.

For each active plugin, calls plugin.generate() to get {path: content} pairs.
Assembles lefthook.yml from all active plugin hook_config() dicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from ai_guardrails.generators.base import HASH_HEADER_PREFIX, compute_hash, verify_hash
from ai_guardrails.infra.config_loader import deep_merge
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext


class GenerateConfigsStep:
    """Runs all active plugins and writes their generated config files."""

    name = "generate-configs"

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
            all_issues.extend(plugin.check(ctx.registry, ctx.project_dir))

        # Also check lefthook.yml staleness
        lefthook_config: dict[str, object] = {}
        for plugin in ctx.languages:
            lefthook_config = deep_merge(lefthook_config, plugin.hook_config())
        if lefthook_config:
            lefthook_path = ctx.project_dir / "lefthook.yml"
            if not lefthook_path.exists():
                all_issues.append(
                    "lefthook.yml is missing — run: ai-guardrails generate"
                )
            else:
                body = yaml.dump(
                    lefthook_config, default_flow_style=False, sort_keys=False
                )
                existing = lefthook_path.read_text()
                if not verify_hash(existing, body):
                    all_issues.append(
                        "lefthook.yml is stale or tampered"
                        " — run: ai-guardrails generate"
                    )

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

        # 1. Generate per-plugin config files
        for plugin in ctx.languages:
            outputs = plugin.generate(ctx.registry, ctx.project_dir)
            for path, content in outputs.items():
                ctx.file_manager.mkdir(path.parent, parents=True, exist_ok=True)
                ctx.file_manager.write_text(path, content)
                generated.append(path.name)

        # 2. Assemble lefthook.yml from all active hook_configs
        lefthook_config: dict[str, object] = {}
        for plugin in ctx.languages:
            lefthook_config = deep_merge(lefthook_config, plugin.hook_config())

        if lefthook_config:
            body = yaml.dump(lefthook_config, default_flow_style=False, sort_keys=False)
            header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
            full_content = f"{header}\n{body}"
            lefthook_path = ctx.project_dir / "lefthook.yml"
            ctx.file_manager.mkdir(lefthook_path.parent, parents=True, exist_ok=True)
            ctx.file_manager.write_text(lefthook_path, full_content)
            generated.append("lefthook.yml")

        if not generated:
            return StepResult(status="ok", message="No configs generated")
        return StepResult(status="ok", message=f"Generated: {', '.join(generated)}")
