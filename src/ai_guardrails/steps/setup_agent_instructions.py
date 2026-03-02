"""SetupAgentInstructionsStep — appends guardrails section to CLAUDE.md.

Appends the guardrails template section to CLAUDE.md if the section is
not already present. Creates CLAUDE.md if it doesn't exist.
"""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.pipelines.base import PipelineContext, StepResult

_SECTION_MARKER = "## AI Guardrails"
_CLAUDE_MD = Path("CLAUDE.md")


class SetupAgentInstructionsStep:
    """Appends guardrails section to CLAUDE.md; skips if already present."""

    name = "setup-agent-instructions"

    def __init__(self, template_path: Path) -> None:
        self._template = template_path

    def validate(self, ctx: PipelineContext) -> list[str]:
        if not self._template.exists():
            return [f"Agent instructions template not found: {self._template}"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        claude_md = ctx.project_dir / _CLAUDE_MD
        template_content = self._template.read_text()

        if ctx.file_manager.exists(claude_md):
            existing = ctx.file_manager.read_text(claude_md)
            if _SECTION_MARKER in existing:
                return StepResult(
                    status="skip",
                    message=f"Guardrails section already in {_CLAUDE_MD}",
                )
            new_content = existing.rstrip("\n") + "\n\n" + template_content
        else:
            new_content = template_content

        ctx.file_manager.write_text(claude_md, new_content)
        return StepResult(status="ok", message=f"Updated {_CLAUDE_MD}")
