"""Generate .codespellrc from project exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from generators import make_header

if TYPE_CHECKING:
    from pathlib import Path

    from registry import ExceptionRegistry

HEADER = make_header()


def generate_codespell(
    registry: ExceptionRegistry,
    output_path: Path,
) -> None:
    """Generate .codespellrc from registry.

    Args:
        registry: Parsed exception registry.
        output_path: Path to write .codespellrc.

    """
    codespell_config = registry.global_rules.get("codespell", {})

    lines = [HEADER, "[codespell]"]

    skip = codespell_config.get("skip", [])
    if skip:
        lines.append(f"skip = {','.join(skip)}")

    ignore_words = codespell_config.get("ignore_words", [])
    if ignore_words:
        lines.append(f"ignore-words-list = {','.join(ignore_words)}")

    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
