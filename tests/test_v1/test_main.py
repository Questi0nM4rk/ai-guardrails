"""Tests for __main__.py entry point."""

from __future__ import annotations

from ai_guardrails.cli import app


def test_main_module_entry_point_is_callable() -> None:
    assert callable(app)
