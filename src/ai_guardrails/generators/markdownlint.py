"""MarkdownlintGenerator — merges base .markdownlint.jsonc with registry exceptions.

Loads the base JSONC config, strips comments, applies global ignore rules
from the exception registry (sets those rule IDs to false), then outputs
the merged config with a hash header using // comment style.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ai_guardrails.generators.base import compute_hash

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry

_HASH_PREFIX = "// ai-guardrails:hash:sha256:"


def _strip_jsonc_comments(text: str) -> str:
    """Remove // line comments from JSONC content."""
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def _make_jsonc_hash_header(content: str) -> str:
    return f"{_HASH_PREFIX}{compute_hash(content)}"


def _parse_jsonc_hash(text: str) -> str | None:
    first_line = text.split("\n", 1)[0].strip()
    if first_line.startswith(_HASH_PREFIX):
        return first_line[len(_HASH_PREFIX) :]
    return None


def _verify_jsonc_hash(full_text: str, body: str) -> bool:
    stored = _parse_jsonc_hash(full_text)
    if stored is None:
        return False
    return stored == compute_hash(body)


class MarkdownlintGenerator:
    """Generates .markdownlint.jsonc by merging base config with registry."""

    name = "markdownlint"
    output_files = [".markdownlint.jsonc"]

    def __init__(self, configs_dir: Path) -> None:
        self._configs_dir = configs_dir

    def _load_base(self) -> dict:  # type: ignore[type-arg]
        src = self._configs_dir / ".markdownlint.jsonc"
        if not src.exists():
            raise FileNotFoundError(src)
        raw = src.read_text()
        return json.loads(_strip_jsonc_comments(raw))

    def _build_body(self, registry: ExceptionRegistry) -> str:
        config = self._load_base()
        for rule in registry.get_ignores("markdownlint"):
            config[rule] = False
        return json.dumps(config, indent=2)

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/.markdownlint.jsonc: content_with_hash_header}."""
        body = self._build_body(registry)
        header = _make_jsonc_hash_header(body)
        full_content = f"{header}\n{body}\n"
        return {project_dir / ".markdownlint.jsonc": full_content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if .markdownlint.jsonc is missing or stale."""
        target = project_dir / ".markdownlint.jsonc"
        if not target.exists():
            return [".markdownlint.jsonc is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        try:
            expected_body = self._build_body(registry)
        except FileNotFoundError:
            return [".markdownlint.jsonc base config not found in package data"]
        if not _verify_jsonc_hash(existing, expected_body):
            return [".markdownlint.jsonc is stale or tampered — run: ai-guardrails generate"]
        return []
