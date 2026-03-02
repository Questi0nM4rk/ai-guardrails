"""LanguageConfig — domain model for configs/languages.yaml.

Single source of truth for detection rules, config file mappings,
and hook templates per language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class DetectionRules:
    """Rules for detecting a language in a project."""

    files: list[str]
    patterns: list[str]
    directories: list[str]


@dataclass
class LanguageConfig:
    """Configuration and detection rules for a single language."""

    key: str
    name: str
    detect: DetectionRules
    configs: list[str]
    hook_template: str

    @classmethod
    def load_all(cls, yaml_path: Path) -> list[LanguageConfig]:
        """Load all language configs from a languages.yaml file."""
        if not yaml_path.exists():
            raise FileNotFoundError(yaml_path)
        with yaml_path.open() as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}

        result: list[LanguageConfig] = []
        for key, data in raw.items():
            detect_raw = data.get("detect", {})
            detect = DetectionRules(
                files=list(detect_raw.get("files", [])),
                patterns=list(detect_raw.get("patterns", [])),
                directories=list(detect_raw.get("directories", [])),
            )
            result.append(
                cls(
                    key=key,
                    name=data.get("name", key),
                    detect=detect,
                    configs=list(data.get("configs", [])),
                    hook_template=data.get("pre_commit_template", ""),
                )
            )
        return result
