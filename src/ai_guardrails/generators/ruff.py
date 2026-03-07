"""RuffGenerator — tamper-protected ruff.toml generation with exception merging.

Reads the base ruff.toml template from _data/configs/ruff.toml, merges
global and per-file ignores from the ExceptionRegistry, then writes the
result prefixed with a sha256 hash header.
"""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import TYPE_CHECKING, ClassVar

import tomli_w

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    verify_hash,
)

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_BASE_TEMPLATE = Path(__file__).parent.parent / "_data" / "configs" / "ruff.toml"
_STALE_MSG = "ruff.toml is stale or tampered — run: ai-guardrails generate"


class RuffGenerator:
    """Generates a tamper-protected ruff.toml by merging base config with exceptions."""

    name = "ruff"
    output_files: ClassVar[list[str]] = ["ruff.toml"]

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],  # ai-guardrails-allow: ARG002 "unused in base"
        project_dir: Path,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
    ) -> dict[Path, str]:
        """Return {Path("ruff.toml"): content} with hash header."""
        body = self._build_body(registry)
        header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
        content = header + "\n" + body
        return {Path("ruff.toml"): content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
        languages: list[str] | None = None,  # ai-guardrails-allow: ARG002 "unused"
    ) -> list[str]:
        """Return stale/missing descriptions (empty list = fresh)."""
        target = project_dir / "ruff.toml"
        if not target.exists():
            return ["ruff.toml is missing — run: ai-guardrails generate"]
        existing = target.read_text(encoding="utf-8")
        expected_body = self._build_body(registry)
        if not verify_hash(existing, expected_body):
            return [_STALE_MSG]
        return []

    def _build_body(self, registry: ExceptionRegistry) -> str:
        """Build the ruff.toml body (without hash header) from template + registry."""
        raw = _BASE_TEMPLATE.read_bytes()
        config: dict = tomllib.loads(raw.decode("utf-8"))

        lint = config.setdefault("lint", {})

        # Merge global ignores from registry
        extra_ignores = registry.get_ignores("ruff")
        if extra_ignores:
            existing = list(lint.get("ignore", []))
            merged = sorted(set(existing) | set(extra_ignores))
            lint["ignore"] = merged

        # Merge per-file-ignores from registry
        per_file = lint.setdefault("per-file-ignores", {})
        registry_pfi = registry.get_per_file_ignores("ruff")
        for glob_pat, rules in registry_pfi.items():
            existing_rules = set(per_file.get(glob_pat, []))
            existing_rules.update(rules)
            per_file[glob_pat] = sorted(existing_rules)

        return tomli_w.dumps(config)
