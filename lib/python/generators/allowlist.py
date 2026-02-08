"""Generate .suppression-allowlist from inline_suppressions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from generators import make_header

if TYPE_CHECKING:
    from pathlib import Path

    from registry import ExceptionRegistry

HEADER = make_header(
    extra_lines=(
        "Each non-comment line is a grep -E pattern matched case-insensitively",
        "against detected suppression comment lines. Only these patterns pass.",
    ),
)


def generate_allowlist(
    registry: ExceptionRegistry,
    output_path: Path,
) -> None:
    """Generate .suppression-allowlist from registry inline suppressions.

    Args:
        registry: Parsed exception registry.
        output_path: Path to write .suppression-allowlist.

    """
    lines = [HEADER]

    for sup in registry.inline_suppressions:
        globs = ", ".join(sup.glob)
        lines.append(f"# {sup.reason} (files: {globs})")
        lines.append(sup.pattern)
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
