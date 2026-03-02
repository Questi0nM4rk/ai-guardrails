"""LefthookGenerator — assembles lefthook.yml from per-language templates.

Algorithm:
- Load templates/lefthook/base.yaml (always included)
- For each detected language, load templates/lefthook/{language}.yaml (if present)
- Deep-merge language templates into base config
- Serialize to YAML and add hash header
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from ai_guardrails.generators.base import compute_hash
from ai_guardrails.infra.config_loader import deep_merge

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry

_HASH_PREFIX = "# ai-guardrails:hash:sha256:"
_HEADER_PLUS_BODY = 2  # split("\n", 1) produces [header, body]


class LefthookGenerator:
    """Generates lefthook.yml by merging base + per-language hook templates."""

    name = "lefthook"
    output_files = ["lefthook.yml"]

    def __init__(self, templates_dir: Path) -> None:
        self._templates_dir = templates_dir

    def _load_yaml(self, path: Path) -> dict:  # type: ignore[type-arg]
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open() as f:
            result = yaml.safe_load(f)
        return result if isinstance(result, dict) else {}

    def _build_config(self, languages: list[str]) -> dict:  # type: ignore[type-arg]
        config = self._load_yaml(self._templates_dir / "base.yaml")

        for lang in languages:
            lang_template = self._templates_dir / f"{lang}.yaml"
            if not lang_template.exists():
                continue
            lang_config = self._load_yaml(lang_template)
            config = deep_merge(config, lang_config)

        return config

    def _build_body(self, languages: list[str]) -> str:
        config = self._build_config(languages)
        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/lefthook.yml: content_with_hash_header}."""
        body = self._build_body(languages)
        header = f"{_HASH_PREFIX}{compute_hash(body)}"
        full_content = f"{header}\n{body}"
        return {project_dir / "lefthook.yml": full_content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if lefthook.yml is missing or stale.

        Note: check() cannot re-detect languages so it hashes the base
        config only. For full freshness checking, callers should pass
        languages to generate() and compare.
        """
        target = project_dir / "lefthook.yml"
        if not target.exists():
            return ["lefthook.yml is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        stored_hash = None
        first_line = existing.split("\n", 1)[0].strip()
        if first_line.startswith(_HASH_PREFIX):
            stored_hash = first_line[len(_HASH_PREFIX) :]
        if stored_hash is None:
            return ["lefthook.yml is stale or tampered — run: ai-guardrails generate"]
        # We verify by recomputing from the body after the header
        parts = existing.split("\n", 1)
        if len(parts) < _HEADER_PLUS_BODY:
            return ["lefthook.yml is stale or tampered — run: ai-guardrails generate"]
        body = parts[1]
        if stored_hash != compute_hash(body):
            return ["lefthook.yml is stale or tampered — run: ai-guardrails generate"]
        return []
