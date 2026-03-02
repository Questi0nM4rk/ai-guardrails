"""GenerateConfigsStep — runs all active language plugins to produce config files.

For each active plugin, calls plugin.generate() to get {path: content} pairs.
Assembles lefthook.yml from all active plugin hook_config() dicts.
"""

from __future__ import annotations

import contextlib

import yaml

from ai_guardrails.generators.base import HASH_HEADER_PREFIX, compute_hash
from ai_guardrails.infra.config_loader import deep_merge
from ai_guardrails.pipelines.base import PipelineContext, StepResult


class GenerateConfigsStep:
    """Runs all active plugins and writes their generated config files."""

    name = "generate-configs"

    def validate(self, ctx: PipelineContext) -> list[str]:
        if ctx.registry is None:
            return ["Registry not loaded — run scaffold-registry first"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        assert ctx.registry is not None  # guaranteed by validate()
        generated: list[str] = []

        # 1. Generate per-plugin config files
        for plugin in ctx.languages:
            outputs = plugin.generate(ctx.registry, ctx.project_dir)
            for path, content in outputs.items():
                with contextlib.suppress(FileExistsError, AttributeError):
                    ctx.file_manager.mkdir(path.parent, parents=True, exist_ok=True)
                ctx.file_manager.write_text(path, content)
                generated.append(path.name)

        # 2. Assemble lefthook.yml from all active hook_configs
        lefthook_config: dict = {}  # type: ignore[type-arg]
        for plugin in ctx.languages:
            lefthook_config = deep_merge(lefthook_config, plugin.hook_config())

        if lefthook_config:
            body = yaml.dump(lefthook_config, default_flow_style=False, sort_keys=False)
            header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
            full_content = f"{header}\n{body}"
            lefthook_path = ctx.project_dir / "lefthook.yml"
            with contextlib.suppress(FileExistsError, AttributeError):
                ctx.file_manager.mkdir(lefthook_path.parent, parents=True, exist_ok=True)
            ctx.file_manager.write_text(lefthook_path, full_content)
            generated.append("lefthook.yml")

        if not generated:
            return StepResult(status="ok", message="No configs generated")
        return StepResult(status="ok", message=f"Generated: {', '.join(generated)}")
