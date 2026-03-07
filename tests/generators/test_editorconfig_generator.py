"""Tests for EditorconfigGenerator — tamper-protected .editorconfig generation."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    parse_hash_header,
)
from ai_guardrails.generators.editorconfig import EditorconfigGenerator
from ai_guardrails.models.registry import ExceptionRegistry


def _registry() -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


def test_editorconfig_generator_name() -> None:
    gen = EditorconfigGenerator()
    assert gen.name == "editorconfig"


def test_editorconfig_generator_output_files() -> None:
    gen = EditorconfigGenerator()
    assert gen.output_files == [".editorconfig"]


def test_editorconfig_generator_produces_hash_header(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    assert content.startswith(HASH_HEADER_PREFIX)


def test_editorconfig_generator_hash_header_is_valid(tmp_path: Path) -> None:
    """Body hash in header must match the actual body."""
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    lines = content.split("\n", 1)
    header_line = lines[0]
    body = lines[1] if len(lines) > 1 else ""
    stored = parse_hash_header(header_line + "\n")
    assert stored == compute_hash(body)


def test_editorconfig_generator_contains_root_true(tmp_path: Path) -> None:
    """Generated .editorconfig must contain root = true."""
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    assert "root = true" in content


def test_editorconfig_generator_contains_utf8(tmp_path: Path) -> None:
    """Generated .editorconfig must set charset = utf-8."""
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    assert "charset = utf-8" in content


def test_editorconfig_generator_contains_lf_line_ending(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    assert "end_of_line = lf" in content


def test_editorconfig_generator_contains_final_newline(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    assert "insert_final_newline = true" in content


def test_editorconfig_generator_is_deterministic(tmp_path: Path) -> None:
    """Two calls with the same registry must produce identical output."""
    gen = EditorconfigGenerator()
    registry = _registry()
    out1 = gen.generate(registry, [], tmp_path)
    out2 = gen.generate(registry, [], tmp_path)
    assert out1[Path(".editorconfig")] == out2[Path(".editorconfig")]


def test_editorconfig_generator_returns_single_file(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    assert list(outputs.keys()) == [Path(".editorconfig")]


# ---------------------------------------------------------------------------
# check() tests
# ---------------------------------------------------------------------------


def test_editorconfig_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    (tmp_path / ".editorconfig").write_text(outputs[Path(".editorconfig")])
    issues = gen.check(registry, tmp_path)
    assert issues == []


def test_editorconfig_check_returns_stale_when_missing(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert ".editorconfig" in issues[0]


def test_editorconfig_check_returns_stale_when_tampered(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".editorconfig")]
    (tmp_path / ".editorconfig").write_text(content + "\n# TAMPERED")
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert ".editorconfig" in issues[0]


def test_editorconfig_check_stale_message_has_generate_hint(tmp_path: Path) -> None:
    gen = EditorconfigGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert any("ai-guardrails generate" in issue for issue in issues)
