"""CodespellGenerator — generates .codespellrc from exception registry.

Generated from scratch based on the [global_rules.codespell] section
of the exception registry. No base config file to merge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.generators.base import make_hash_header, verify_hash

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry


class CodespellGenerator:
    """Generates .codespellrc from exception registry codespell section."""

    name = "codespell"
    output_files = [".codespellrc"]

    def _build_body(self, registry: ExceptionRegistry) -> str:
        codespell_config = registry.global_rules.get("codespell", {})
        lines = ["[codespell]"]

        skip = codespell_config.get("skip", [])
        if skip:
            lines.append(f"skip = {','.join(skip)}")

        ignore_words = codespell_config.get("ignore_words", [])
        if ignore_words:
            lines.append(f"ignore-words-list = {','.join(ignore_words)}")

        lines.append("")
        return "\n".join(lines)

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/.codespellrc: content_with_hash_header}."""
        body = self._build_body(registry)
        header = make_hash_header(body)
        full_content = f"{header}\n{body}"
        return {project_dir / ".codespellrc": full_content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if .codespellrc is missing or stale."""
        target = project_dir / ".codespellrc"
        if not target.exists():
            return [".codespellrc is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        expected_body = self._build_body(registry)
        if not verify_hash(existing, expected_body):
            return [".codespellrc is stale or tampered — run: ai-guardrails generate"]
        return []
