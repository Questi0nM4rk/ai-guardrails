"""Tests for AgentRulesGenerator — 5 hash-protected agent instruction files."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from ai_guardrails.generators.agent_rules import AgentRulesGenerator
from ai_guardrails.generators.base import parse_hash_header
from ai_guardrails.models.registry import ExceptionRegistry
from tests.conftest import TEMPLATES_DIR

if TYPE_CHECKING:
    from pathlib import Path


def _make_registry() -> ExceptionRegistry:
    return MagicMock(spec=ExceptionRegistry)


def _make_generator() -> AgentRulesGenerator:
    return AgentRulesGenerator(templates_dir=TEMPLATES_DIR / "agent-rules")


# --- generate produces all 5 files ---


def test_agent_rules_generator_produces_4_files(tmp_path: Path):
    # CLAUDE.md is managed by SetupAgentInstructionsStep (v1) until v2 retirement.
    gen = _make_generator()
    result = gen.generate(_make_registry(), [], tmp_path)
    assert len(result) == 4
    names = {p.name for p in result}
    assert "AGENTS.md" in names
    assert ".cursorrules" in names
    assert ".windsurfrules" in names
    assert "copilot-instructions.md" in {p.name for p in result}


def test_agents_md_contains_base_content(tmp_path: Path):
    gen = _make_generator()
    result = gen.generate(_make_registry(), [], tmp_path)
    path = next(p for p in result if p.name == "AGENTS.md")
    content = result[path]
    assert "AI Agent Rules" in content
    assert "Exception Protocol" in content


def test_cursorrules_contains_base_and_additions(tmp_path: Path):
    gen = _make_generator()
    result = gen.generate(_make_registry(), [], tmp_path)
    path = next(p for p in result if p.name == ".cursorrules")
    content = result[path]
    assert "AI Agent Rules" in content  # base
    assert "Cursor Rules" in content  # cursor-additions


def test_windsurfrules_contains_base_and_additions(tmp_path: Path):
    gen = _make_generator()
    result = gen.generate(_make_registry(), [], tmp_path)
    path = next(p for p in result if p.name == ".windsurfrules")
    content = result[path]
    assert "AI Agent Rules" in content  # base
    assert "Windsurf Rules" in content  # windsurf-additions


def test_copilot_instructions_contains_base_and_additions(tmp_path: Path):
    gen = _make_generator()
    result = gen.generate(_make_registry(), [], tmp_path)
    path = next(p for p in result if p.name == "copilot-instructions.md")
    content = result[path]
    assert "AI Agent Rules" in content  # base
    assert "GitHub Copilot Rules" in content  # copilot-additions


# --- hash protection ---


def test_all_generated_files_have_hash_headers(tmp_path: Path):
    gen = _make_generator()
    result = gen.generate(_make_registry(), [], tmp_path)
    for path, content in result.items():
        assert parse_hash_header(content) is not None, (
            f"{path.name} missing hash header"
        )


# --- check method ---


def test_check_returns_empty_when_all_fresh(tmp_path: Path):
    gen = _make_generator()
    registry = _make_registry()
    generated = gen.generate(registry, [], tmp_path)
    for rel_path, content in generated.items():
        (tmp_path / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel_path).write_text(content)
    stale = gen.check(registry, tmp_path)
    assert stale == []


def test_check_returns_stale_when_file_missing(tmp_path: Path):
    gen = _make_generator()
    stale = gen.check(_make_registry(), tmp_path)
    assert len(stale) == 4  # all missing (CLAUDE.md is managed separately)


def test_check_returns_stale_when_content_tampered(tmp_path: Path):
    gen = _make_generator()
    registry = _make_registry()
    generated = gen.generate(registry, [], tmp_path)
    for rel_path, content in generated.items():
        (tmp_path / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel_path).write_text(content)
    # Tamper with AGENTS.md
    agents_md = tmp_path / "AGENTS.md"
    original = agents_md.read_text()
    agents_md.write_text(original + "\nmalicious content\n")
    stale = gen.check(registry, tmp_path)
    assert any("AGENTS.md" in s for s in stale)
