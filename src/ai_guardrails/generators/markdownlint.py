"""MarkdownlintGenerator — tamper-protected .markdownlint.jsonc generation.

Reads the base .markdownlint.jsonc template from _data/configs/, merges
disabled rules from ExceptionRegistry, then writes the result prefixed
with a JSONC-style sha256 hash header.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, ClassVar

from ai_guardrails.generators.base import (
    JSONC_HASH_HEADER_PREFIX,
    compute_hash,
    verify_hash,
)

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_BASE_TEMPLATE = (
    Path(__file__).parent.parent / "_data" / "configs" / ".markdownlint.jsonc"
)
_STALE_MSG = ".markdownlint.jsonc is stale or tampered — run: ai-guardrails generate"


def _strip_jsonc_comments(text: str) -> str:
    """Remove single-line // comments from JSONC content."""
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


class MarkdownlintGenerator:
    """Generates tamper-protected .markdownlint.jsonc with exception merging."""

    name = "markdownlint"
    output_files: ClassVar[list[str]] = [".markdownlint.jsonc"]

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],  # noqa: ARG002
        project_dir: Path,  # noqa: ARG002
    ) -> dict[Path, str]:
        """Return {Path(".markdownlint.jsonc"): content} with hash header."""
        body = self._build_body(registry)
        header = f"{JSONC_HASH_HEADER_PREFIX}{compute_hash(body)}"
        content = header + "\n" + body
        return {Path(".markdownlint.jsonc"): content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
        languages: list[str] | None = None,  # noqa: ARG002
    ) -> list[str]:
        """Return stale/missing descriptions (empty list = fresh)."""
        target = project_dir / ".markdownlint.jsonc"
        if not target.exists():
            return [".markdownlint.jsonc is missing — run: ai-guardrails generate"]
        existing = target.read_text(encoding="utf-8")
        expected_body = self._build_body(registry)
        if not verify_hash(existing, expected_body):
            return [_STALE_MSG]
        return []

    def _build_body(self, registry: ExceptionRegistry) -> str:
        """Build the .markdownlint.jsonc body from template + registry."""
        raw = _BASE_TEMPLATE.read_text(encoding="utf-8")
        stripped = _strip_jsonc_comments(raw)
        config: dict = json.loads(stripped)

        # Disable rules from registry
        for rule in registry.get_ignores("markdownlint"):
            config[rule] = False

        return json.dumps(config, indent=2)
