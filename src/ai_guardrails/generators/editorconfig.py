"""EditorconfigGenerator — tamper-protected .editorconfig generation.

Produces a standard .editorconfig with language-specific overrides.
No exception merging — the content is always the same standard config.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    verify_hash,
)

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_BASE_TEMPLATE = Path(__file__).parent.parent / "_data" / "configs" / ".editorconfig"


class EditorconfigGenerator:
    """Generates a tamper-protected .editorconfig with standard content."""

    name = "editorconfig"
    output_files: ClassVar[list[str]] = [".editorconfig"]

    def generate(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        languages: list[str],  # noqa: ARG002
        project_dir: Path,  # noqa: ARG002
    ) -> dict[Path, str]:
        """Return {Path(".editorconfig"): content} with hash header."""
        body = _BASE_TEMPLATE.read_text(encoding="utf-8")
        header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
        content = header + "\n" + body
        return {Path(".editorconfig"): content}

    def check(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        project_dir: Path,
    ) -> list[str]:
        """Return stale/missing descriptions (empty list = fresh)."""
        target = project_dir / ".editorconfig"
        if not target.exists():
            return [".editorconfig is missing — run: ai-guardrails generate"]
        body = _BASE_TEMPLATE.read_text(encoding="utf-8")
        existing = target.read_text(encoding="utf-8")
        if not verify_hash(existing, body):
            return [".editorconfig is stale or tampered — run: ai-guardrails generate"]
        return []
