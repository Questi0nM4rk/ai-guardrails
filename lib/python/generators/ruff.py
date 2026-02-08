"""Generate ruff.toml by merging base template with project exceptions."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import tomli_w
from generators import make_header

if TYPE_CHECKING:
    from pathlib import Path

    from registry import ExceptionRegistry

HEADER = make_header() + "\n"


def generate_ruff(
    registry: ExceptionRegistry,
    base_path: Path,
    output_path: Path,
) -> None:
    """Merge base ruff.toml with registry exceptions.

    Args:
        registry: Parsed exception registry.
        base_path: Path to base ruff.toml template.
        output_path: Path to write merged ruff.toml.

    """
    with base_path.open("rb") as f:
        config = tomllib.load(f)

    lint = config.setdefault("lint", {})

    # Merge global ignores
    existing_ignores = set(lint.get("ignore", []))
    new_ignores = set(registry.get_global_ignores("ruff"))
    lint["ignore"] = sorted(existing_ignores | new_ignores)

    # Merge per-file-ignores
    pfi = lint.setdefault("per-file-ignores", {})
    for fe in registry.get_file_exceptions("ruff"):
        for glob_pattern in fe.glob:
            existing = set(pfi.get(glob_pattern, []))
            pfi[glob_pattern] = sorted(existing | set(fe.rules))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        f.write(HEADER.encode())
        tomli_w.dump(config, f)
