"""LanguagePlugin protocol and BaseLanguagePlugin convenience class.

Each language plugin encapsulates:
- Detection rules (files, glob patterns, directories)
- Config files to copy (copy_files)
- Config files to generate (generated_configs)
- generate() — produces {path: content} for generated files
- hook_config() — returns dict merged into lefthook.yml
- check() — returns list of stale/missing descriptions
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  # used at runtime in glob and Protocol
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".env",
        "node_modules",
        ".ai-guardrails",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "dist",
        "build",
        ".eggs",
        "fixtures",
    }
)


@runtime_checkable
class LanguagePlugin(Protocol):
    """Protocol that all language plugins must satisfy."""

    key: str
    name: str
    copy_files: list[str]
    generated_configs: list[str]

    def detect(self, project_dir: Path) -> bool:
        """Return True if this language is present in project_dir."""
        ...

    def generate(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {path: content} for all files this plugin generates."""
        ...

    def hook_config(self) -> dict[str, object]:
        """Return dict to be deep-merged into lefthook.yml."""
        ...

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return list of stale/missing config descriptions (empty = fresh)."""
        ...


def _glob_matches_source(project_dir: Path, pattern: str) -> bool:
    """Return True if pattern matches any file outside _SKIP_DIRS."""
    for match in project_dir.glob(f"**/{pattern}"):
        parts = match.relative_to(project_dir).parts
        if not any(part in _SKIP_DIRS for part in parts):
            return True
    return False


class BaseLanguagePlugin:
    """Convenience base class providing standard detect() implementation.

    Subclasses set class attributes to configure detection and copy/generate
    metadata. Override generate(), hook_config(), and check() as needed.
    """

    key: ClassVar[str] = ""
    name: ClassVar[str] = ""
    detect_files: ClassVar[list[str]] = []
    detect_patterns: ClassVar[list[str]] = []
    detect_dirs: ClassVar[list[str]] = []
    copy_files: ClassVar[list[str]] = []
    generated_configs: ClassVar[list[str]] = []

    def detect(self, project_dir: Path) -> bool:
        """Return True if language detected in project_dir."""
        # 1. Exact file match in project root
        if any((project_dir / f).exists() for f in self.detect_files):
            return True
        # 2. Glob pattern match (skipping vendor/generated dirs)
        for pattern in self.detect_patterns:
            if _glob_matches_source(project_dir, pattern):
                return True
        # 3. Directory presence
        return any((project_dir / d).is_dir() for d in self.detect_dirs)

    def generate(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        project_dir: Path,  # noqa: ARG002
    ) -> dict[Path, str]:
        """Return empty dict — subclasses override to generate files."""
        return {}

    def hook_config(self) -> dict[str, object]:
        """Return empty dict — subclasses override to provide hook config."""
        return {}

    def check(
        self,
        registry: ExceptionRegistry,  # noqa: ARG002
        project_dir: Path,  # noqa: ARG002
    ) -> list[str]:
        """Return empty list — subclasses override to validate generated files."""
        return []
