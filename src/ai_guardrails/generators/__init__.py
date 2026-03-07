"""Hash utilities and default generator list for ai-guardrails generated configs."""

from __future__ import annotations

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    Generator,
    compute_hash,
    make_hash_header,
    verify_hash,
)
from ai_guardrails.generators.editorconfig import EditorconfigGenerator
from ai_guardrails.generators.lefthook import LefthookGenerator
from ai_guardrails.generators.markdownlint import MarkdownlintGenerator
from ai_guardrails.generators.ruff import RuffGenerator

DEFAULT_GENERATORS: list[Generator] = [
    RuffGenerator(),
    MarkdownlintGenerator(),
    EditorconfigGenerator(),
    LefthookGenerator(),
]

__all__ = [
    "DEFAULT_GENERATORS",
    "HASH_HEADER_PREFIX",
    "Generator",
    "compute_hash",
    "make_hash_header",
    "verify_hash",
]
