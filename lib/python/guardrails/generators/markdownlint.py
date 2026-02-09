"""Generate .markdownlint.jsonc by merging base with project exceptions."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from guardrails.generators import make_header

if TYPE_CHECKING:
    from pathlib import Path

    from guardrails.registry import ExceptionRegistry

HEADER = make_header("//")


def _strip_jsonc_comments(text: str) -> str:
    """Remove // comments from JSONC content."""
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def generate_markdownlint(
    registry: ExceptionRegistry,
    base_path: Path,
    output_path: Path,
) -> None:
    """Merge base .markdownlint.jsonc with registry exceptions.

    Args:
        registry: Parsed exception registry.
        base_path: Path to base .markdownlint.jsonc template.
        output_path: Path to write merged .markdownlint.jsonc.

    """
    raw = base_path.read_text()
    config = json.loads(_strip_jsonc_comments(raw))

    # Disable rules listed in exceptions
    disabled_rules = registry.get_global_ignores("markdownlint")
    for rule in disabled_rules:
        config[rule] = False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [HEADER]
    lines.append(json.dumps(config, indent=2))
    lines.append("")
    output_path.write_text("\n".join(lines))
