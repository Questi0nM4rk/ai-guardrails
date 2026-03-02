"""Generator implementations for ai-guardrails v1.

Each generator produces one or more config files from the exception registry
and optionally base config templates.
"""

from __future__ import annotations

from ai_guardrails.generators.base import Generator
from ai_guardrails.generators.claude_settings import ClaudeSettingsGenerator
from ai_guardrails.generators.codespell import CodespellGenerator
from ai_guardrails.generators.editorconfig import EditorconfigGenerator
from ai_guardrails.generators.lefthook import LefthookGenerator
from ai_guardrails.generators.markdownlint import MarkdownlintGenerator
from ai_guardrails.generators.ruff import RuffGenerator

__all__ = [
    "ClaudeSettingsGenerator",
    "CodespellGenerator",
    "EditorconfigGenerator",
    "Generator",
    "LefthookGenerator",
    "MarkdownlintGenerator",
    "RuffGenerator",
]
