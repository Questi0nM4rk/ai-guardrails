"""AgentRulesGenerator — generate tamper-protected agent instruction files.

Produces four files, each composed of base.md + agent-specific additions:
  AGENTS.md                       — canonical, all agents
  .cursorrules                    — base + cursor-additions.md
  .windsurfrules                  — base + windsurf-additions.md
  .github/copilot-instructions.md — base + copilot-additions.md

Note: CLAUDE.md is managed by SetupAgentInstructionsStep (v1 compat).
It will be merged here when SetupAgentInstructionsStep is retired in v2.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.generators.base import make_md_hash_header, verify_hash

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_DEFAULT_TEMPLATES_DIR = (
    Path(__file__).parent.parent / "_data" / "templates" / "agent-rules"
)

# (output_path_relative_to_project, additions_filename | None)
_OUTPUTS: list[tuple[str, str | None]] = [
    ("AGENTS.md", None),
    (".cursorrules", "cursor-additions.md"),
    (".windsurfrules", "windsurf-additions.md"),
    (".github/copilot-instructions.md", "copilot-additions.md"),
]


class AgentRulesGenerator:
    """Generates all agent instruction files from base + per-agent templates."""

    name = "agent-rules"
    output_files: ClassVar[list[str]] = [out for out, _ in _OUTPUTS]

    def __init__(self, *, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir or _DEFAULT_TEMPLATES_DIR

    def generate(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        languages: list[str],  # noqa: ARG002
        project_dir: Path,  # noqa: ARG002
    ) -> dict[Path, str]:
        """Return {relative_path: full_content} for all agent files."""
        base = (self._templates_dir / "base.md").read_text(encoding="utf-8")
        result: dict[Path, str] = {}
        for rel, additions_name in _OUTPUTS:
            body = base
            if additions_name:
                extra = (self._templates_dir / additions_name).read_text(
                    encoding="utf-8"
                )
                body = body + "\n" + extra
            header = make_md_hash_header(body)
            content = header + "\n" + body
            result[Path(rel)] = content
        return result

    def check(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        project_dir: Path,
    ) -> list[str]:
        """Return descriptions of stale or missing agent files (empty = all fresh)."""
        base = (self._templates_dir / "base.md").read_text(encoding="utf-8")
        stale: list[str] = []
        for rel, additions_name in _OUTPUTS:
            body = base
            if additions_name:
                extra = (self._templates_dir / additions_name).read_text(
                    encoding="utf-8"
                )
                body = body + "\n" + extra
            path = project_dir / rel
            if not path.exists():
                stale.append(f"{rel} — missing")
                continue
            full = path.read_text(encoding="utf-8")
            if not verify_hash(full, body):
                stale.append(f"{rel} — stale or tampered")
        return stale
