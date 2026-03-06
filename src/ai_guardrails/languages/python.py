"""PythonPlugin — detects Python projects, generates ruff.toml."""

from __future__ import annotations

import tomllib  # type: ignore[no-redef]
from typing import TYPE_CHECKING, ClassVar

import tomli_w
import yaml

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

    _HOOKS_YAML = """\
pre-commit:
  commands:
    python-format-and-stage:
      glob: "*.py"
      run: >-
        uv run ruff format {staged_files} &&
        uv run ruff check --fix {staged_files} &&
        git add {staged_files}
      stage_fixed: true
      priority: 1
    ruff-check:
      glob: "*.py"
      run: uv run ruff check {staged_files}
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def _load_base(self) -> dict[str, object]:
        src = self._configs_dir / "ruff.toml"
        if not src.exists():
            raise FileNotFoundError(src)
        with src.open("rb") as f:
            return tomllib.load(f)

    def _build_config(self, registry: ExceptionRegistry) -> dict[str, object]:
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

        # Apply custom overrides
        if "ruff" in registry.custom:
            config = deep_merge(config, registry.custom["ruff"])

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

    def hook_config(self) -> dict[str, object]:
        """Return Python pre-commit hooks config."""
        return yaml.safe_load(self._HOOKS_YAML) or {}

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
