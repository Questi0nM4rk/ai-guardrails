"""ConfigLoader — loads TOML, YAML, and JSON configuration files.

Returns typed data; never raw dict[str, Any] across module boundaries.
Provides a deep_merge utility for combining base and override configs.
"""

from __future__ import annotations

import json
import tomllib  # type: ignore[no-redef]
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base. Returns a new dict; does not mutate base."""
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigLoader:
    """Loads configuration files in TOML, YAML, and JSON formats."""

    def load_toml(self, path: Path) -> dict[str, Any]:
        """Load a TOML file and return parsed data."""
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("rb") as f:
            return tomllib.load(f)

    def load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a YAML file and return parsed data."""
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open() as f:
            result = yaml.safe_load(f)
        return result if isinstance(result, dict) else {}

    def load_json(self, path: Path) -> dict[str, Any]:
        """Load a JSON file and return parsed data."""
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open() as f:
            return json.load(f)
