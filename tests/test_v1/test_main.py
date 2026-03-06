"""Tests for __main__.py entry point."""

from __future__ import annotations


def test_main_module_entry_point_is_callable():
    """Verify __main__.py exports a callable app."""
    from ai_guardrails.cli import app

    assert callable(app)
