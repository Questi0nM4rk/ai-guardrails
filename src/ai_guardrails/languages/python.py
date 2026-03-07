"""PythonPlugin — detects Python projects, generates ruff.toml."""

from __future__ import annotations

import tomllib  # type: ignore[no-redef]
from typing import TYPE_CHECKING, Any, ClassVar

import tomli_w

from ai_guardrails.generators.base import HASH_HEADER_PREFIX, compute_hash, verify_hash
from ai_guardrails.infra.config_loader import deep_merge
from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry


class PythonPlugin(BaseLanguagePlugin):
    """Language plugin for Python projects."""

    key = "python"
    name = "Python"
    detect_files: ClassVar[list[str]] = [
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
    ]
    detect_patterns: ClassVar[list[str]] = ["*.py"]
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = ["ruff.toml"]

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def _load_base(self) -> dict[str, Any]:
        src = self._configs_dir / "ruff.toml"
        if not src.exists():
            raise FileNotFoundError(src)
        with src.open("rb") as f:
            return tomllib.load(f)

    def _build_config(self, registry: ExceptionRegistry) -> dict[str, Any]:
        config = self._load_base()

        # Save base ignores/per-file-ignores before deep_merge can clobber them
        base_lint = config.get("lint", {})
        base_ignores: set[str] = set(base_lint.get("ignore", []))
        base_pfi: dict[str, list[str]] = dict(base_lint.get("per-file-ignores", {}))

        # Apply custom overrides (may replace arrays — that's OK, we re-merge)
        if "ruff" in registry.custom:
            config = deep_merge(config, registry.custom["ruff"])

        lint = config.setdefault("lint", {})

        # Union all ignore sources: base + custom + registry (sorted)
        custom_ignores: set[str] = set(lint.get("ignore", []))
        registry_ignores: set[str] = set(registry.get_ignores("ruff"))
        lint["ignore"] = sorted(base_ignores | custom_ignores | registry_ignores)

        # Union all per-file-ignores: base + custom + registry (sorted per glob)
        pfi = lint.setdefault("per-file-ignores", {})
        all_globs = (
            set(base_pfi) | set(pfi) | set(registry.get_per_file_ignores("ruff"))
        )
        for glob_pattern in sorted(all_globs):
            merged: set[str] = set(base_pfi.get(glob_pattern, []))
            merged |= set(pfi.get(glob_pattern, []))
            for rule in registry.get_per_file_ignores("ruff").get(glob_pattern, []):
                merged.add(rule)
            pfi[glob_pattern] = sorted(merged)

        return config

    def _build_body(self, registry: ExceptionRegistry) -> str:
        config = self._build_config(registry)
        return tomli_w.dumps(config)

    def generate(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/ruff.toml: content_with_hash_header}."""
        body = self._build_body(registry)
        header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
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
