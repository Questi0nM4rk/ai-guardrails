"""Merge pyright settings from registry into pyproject.toml."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tomlkit

if TYPE_CHECKING:
    from pathlib import Path

    from guardrails.registry import ExceptionRegistry


def generate_pyright(
    registry: ExceptionRegistry,
    pyproject_path: Path,
) -> None:
    """Merge pyright settings from registry into pyproject.toml.

    Uses tomlkit for format-preserving edits.

    Args:
        registry: Parsed exception registry.
        pyproject_path: Path to pyproject.toml to update in place.

    """
    pyright_config = registry.global_rules.get("pyright", {})
    if not pyright_config:
        return

    content = pyproject_path.read_text()
    doc = tomlkit.parse(content)

    tool = doc.setdefault("tool", {})
    pyright_section = tool.setdefault("pyright", {})

    for key, value in pyright_config.items():
        pyright_section[key] = value

    pyproject_path.write_text(tomlkit.dumps(doc))
