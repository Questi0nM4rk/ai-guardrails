"""GenerateAgentRulesStep — write all 5 tamper-protected agent instruction files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators.agent_rules import AgentRulesGenerator
from ai_guardrails.pipelines.base import StepResult

if TYPE_CHECKING:
    from ai_guardrails.pipelines.base import PipelineContext


class GenerateAgentRulesStep:
    """Generates tamper-protected agent instruction files.

    Writes AGENTS.md and IDE-specific rule files (.cursorrules, .windsurfrules,
    .github/copilot-instructions.md). Skips any path that is already a symlink
    (e.g. AGENTS.md → CLAUDE.md created by SetupAgentInstructionsStep in v1).
    """

    name = "generate-agent-rules"

    def __init__(self, generator: AgentRulesGenerator | None = None) -> None:
        self._generator = generator or AgentRulesGenerator()

    def validate(
        self,
        ctx: PipelineContext,  # ai-guardrails-allow: ARG002 "PipelineStep protocol"
    ) -> list[str]:
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        if ctx.check:
            return self._run_check(ctx)
        return self._run_generate(ctx)

    def _run_check(self, ctx: PipelineContext) -> StepResult:
        if ctx.registry is None:
            return StepResult(status="skip", message="Registry not loaded")
        registry = ctx.registry
        # Filter: skip files that are symlinks (managed by SetupAgentInstructionsStep).
        stale = [
            s
            for s in self._generator.check(registry, ctx.project_dir)
            if not (ctx.project_dir / s.split(" — ")[0]).is_symlink()
        ]
        if stale:
            for issue in stale:
                ctx.console.error(issue)
            return StepResult(
                status="error",
                message=f"{len(stale)} agent rule file(s) stale or missing",
            )
        return StepResult(status="ok", message="Agent rule files are fresh")

    def _run_generate(self, ctx: PipelineContext) -> StepResult:
        if ctx.registry is None:
            return StepResult(status="skip", message="Registry not loaded")
        registry = ctx.registry
        outputs = self._generator.generate(registry, [], ctx.project_dir)
        written = 0
        for rel_path, content in outputs.items():
            abs_path = ctx.project_dir / rel_path
            # Skip symlinks — managed by SetupAgentInstructionsStep (v1 compat).
            # Writing through a symlink would clobber the target unexpectedly.
            if abs_path.is_symlink():
                continue
            ctx.file_manager.mkdir(abs_path.parent, parents=True, exist_ok=True)
            ctx.file_manager.write_text(abs_path, content)
            written += 1
        return StepResult(
            status="ok",
            message=f"Generated {written} agent rule file(s)",
        )
