"""DetectLanguagesStep — detects languages present in the project directory.

Uses LanguageConfig detection rules (exact files, glob patterns, directories).
Skips vendored/generated directories to avoid false positives.
Updates ctx.languages in-place.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_guardrails.models.language import LanguageConfig
from ai_guardrails.pipelines.base import PipelineContext, StepResult

if TYPE_CHECKING:
    from pathlib import Path

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
    }
)


def _glob_matches_source(project_dir: Path, pattern: str) -> bool:
    """Return True if pattern matches any file outside skip dirs."""
    for match in project_dir.glob(f"**/{pattern}"):
        parts = match.relative_to(project_dir).parts
        if not any(part in _SKIP_DIRS for part in parts):
            return True
    return False


def _detect(project_dir: Path, lang: LanguageConfig) -> bool:
    """Return True if the language is detected in project_dir."""
    # 1. Exact file match in root
    if any((project_dir / f).exists() for f in lang.detect.files):
        return True
    # 2. Glob patterns (skipping non-source dirs)
    for pattern in lang.detect.patterns:
        if _glob_matches_source(project_dir, pattern):
            return True
    # 3. Directory presence
    return any((project_dir / d).is_dir() for d in lang.detect.directories)


class DetectLanguagesStep:
    """Scans the project directory and sets ctx.languages."""

    name = "detect-languages"

    def __init__(self, languages_yaml: Path) -> None:
        self._languages_yaml = languages_yaml

    def validate(self, ctx: PipelineContext) -> list[str]:
        if not self._languages_yaml.exists():
            return [f"languages.yaml not found: {self._languages_yaml}"]
        return []

    def execute(self, ctx: PipelineContext) -> StepResult:
        all_langs = LanguageConfig.load_all(self._languages_yaml)
        detected = [lang for lang in all_langs if _detect(ctx.project_dir, lang)]
        ctx.languages = detected

        if not detected:
            return StepResult(
                status="warn",
                message="No languages detected — check your project structure",
            )
        names = ", ".join(lang.name for lang in detected)
        return StepResult(status="ok", message=f"Detected: {names}")
