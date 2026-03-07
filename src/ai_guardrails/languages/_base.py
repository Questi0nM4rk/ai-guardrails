"""LanguagePlugin protocol and BaseLanguagePlugin convenience class.

Each language plugin encapsulates:
- Detection rules (files, glob patterns, directories)
- Config files to copy (copy_files)
- Config files to generate (generated_configs)
- generate() — produces {path: content} for generated files
- check() — returns list of stale/missing descriptions
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

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
    linter: str  # lint tool this plugin uses ("ruff", "eslint", …); "" = none
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
    metadata. Override generate() and check() as needed.
    """

    key: ClassVar[str] = ""
    name: ClassVar[str] = ""
    linter: ClassVar[str] = ""  # override in subclasses that run a lint tool
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
        registry: ExceptionRegistry,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
        project_dir: Path,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
    ) -> dict[Path, str]:
        """Return empty dict — subclasses override to generate files."""
        return {}

    def check(
        self,
        registry: ExceptionRegistry,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
        project_dir: Path,  # ai-guardrails-allow: ARG002, E501 "LanguagePlugin protocol — unused in base implementation"
    ) -> list[str]:
        """Return empty list — subclasses override to validate generated files."""
        return []
