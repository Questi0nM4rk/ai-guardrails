"""RuffGenerator — merges base ruff.toml with exception registry.

Algorithm:
- Load base ruff.toml via tomllib
- Union global ignores from registry into lint.ignore
- Union per-file-ignores from registry into lint.per-file-ignores
- Merge custom.ruff from registry into the config (deep merge)
- Add hash header: # ai-guardrails:hash:sha256:<hash>
- Serialize to TOML via tomli_w
"""

from __future__ import annotations

import tomllib  # type: ignore[no-redef]
from typing import TYPE_CHECKING

import tomli_w

from ai_guardrails.generators.base import compute_hash, verify_hash
from ai_guardrails.infra.config_loader import deep_merge

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry

_HASH_PREFIX = "# ai-guardrails:hash:sha256:"


class RuffGenerator:
    """Generates ruff.toml by merging base config with exception registry."""

    name = "ruff"
    output_files = ["ruff.toml"]

    def __init__(self, configs_dir: Path) -> None:
        self._configs_dir = configs_dir

    def _load_base(self) -> dict:  # type: ignore[type-arg]
        src = self._configs_dir / "ruff.toml"
        if not src.exists():
            raise FileNotFoundError(src)
        with src.open("rb") as f:
            return tomllib.load(f)

    def _build_config(self, registry: ExceptionRegistry) -> dict:  # type: ignore[type-arg]
        config = self._load_base()
        lint = config.setdefault("lint", {})

        # Merge global ignores (union, sorted)
        existing_ignores: set[str] = set(lint.get("ignore", []))
        new_ignores: set[str] = set(registry.get_ignores("ruff"))
        lint["ignore"] = sorted(existing_ignores | new_ignores)

        # Merge per-file-ignores (union per glob)
        pfi = lint.setdefault("per-file-ignores", {})
        for glob_pattern, rules in registry.get_per_file_ignores("ruff").items():
            existing: set[str] = set(pfi.get(glob_pattern, []))
            pfi[glob_pattern] = sorted(existing | set(rules))

        # Apply custom overrides (raw deep merge)
        if "ruff" in registry.custom:
            config = deep_merge(config, registry.custom["ruff"])

        return config

    def _build_body(self, registry: ExceptionRegistry) -> str:
        config = self._build_config(registry)
        return tomli_w.dumps(config)

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/ruff.toml: content_with_hash_header}."""
        body = self._build_body(registry)
        header = f"{_HASH_PREFIX}{compute_hash(body)}"
        full_content = f"{header}\n{body}"
        return {project_dir / "ruff.toml": full_content}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if ruff.toml is missing or stale."""
        target = project_dir / "ruff.toml"
        if not target.exists():
            return ["ruff.toml is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        try:
            expected_body = self._build_body(registry)
        except FileNotFoundError:
            return ["ruff.toml base config not found in package data"]
        if not verify_hash(existing, expected_body):
            return ["ruff.toml is stale or tampered — run: ai-guardrails generate"]
        return []
