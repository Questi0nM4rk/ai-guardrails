"""ProjectInfo — domain model describing a project's current state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.language import LanguageConfig


@dataclass
class ProjectInfo:
    """Describes the state of a project as seen by ai-guardrails."""

    root: Path
    languages: list[LanguageConfig]
    has_registry: bool
    has_ci: bool
    has_claude_settings: bool
