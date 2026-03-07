"""Tests for MarkdownlintGenerator — tamper-protected .markdownlint.jsonc generation."""

from __future__ import annotations

import json
from pathlib import Path

from ai_guardrails.generators.base import (
    JSONC_HASH_HEADER_PREFIX,
    compute_hash,
    parse_hash_header,
)
from ai_guardrails.generators.markdownlint import MarkdownlintGenerator
from ai_guardrails.models.registry import ExceptionRegistry


def _registry(
    *,
    global_rules: dict | None = None,
) -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": global_rules or {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


def test_markdownlint_generator_name() -> None:
    gen = MarkdownlintGenerator()
    assert gen.name == "markdownlint"


def test_markdownlint_generator_output_files() -> None:
    gen = MarkdownlintGenerator()
    assert gen.output_files == [".markdownlint.jsonc"]


def test_markdownlint_generator_produces_jsonc_hash_header(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    assert content.startswith(JSONC_HASH_HEADER_PREFIX)


def test_markdownlint_generator_hash_header_is_valid(tmp_path: Path) -> None:
    """Body hash in header must match the actual body."""
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    lines = content.split("\n", 1)
    header_line = lines[0]
    body = lines[1] if len(lines) > 1 else ""
    stored = parse_hash_header(header_line + "\n")
    assert stored == compute_hash(body)


def test_markdownlint_generator_produces_valid_json_body(tmp_path: Path) -> None:
    """Body (after header line) must be valid JSON."""
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    body = content.split("\n", 1)[1]
    parsed = json.loads(body)
    assert isinstance(parsed, dict)


def test_markdownlint_generator_contains_default_true(tmp_path: Path) -> None:
    """Generated config must include default: true from base template."""
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    body = content.split("\n", 1)[1]
    parsed = json.loads(body)
    assert parsed.get("default") is True


def test_markdownlint_generator_disables_registry_rules(tmp_path: Path) -> None:
    """Rules in registry markdownlint exceptions must be set to false."""
    gen = MarkdownlintGenerator()
    registry = _registry(
        global_rules={"markdownlint": {"ignore": ["MD013", "MD024"]}},
    )
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    body = content.split("\n", 1)[1]
    parsed = json.loads(body)
    assert parsed["MD013"] is False
    assert parsed["MD024"] is False


def test_markdownlint_generator_no_exceptions_preserves_base(tmp_path: Path) -> None:
    """Empty registry keeps base template rules unchanged."""
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    assert Path(".markdownlint.jsonc") in outputs
    content = outputs[Path(".markdownlint.jsonc")]
    assert len(content) > 0


def test_markdownlint_generator_returns_single_file(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    assert list(outputs.keys()) == [Path(".markdownlint.jsonc")]


def test_markdownlint_generator_non_markdownlint_rules_ignored(tmp_path: Path) -> None:
    """Rules for other tools must not appear in .markdownlint.jsonc."""
    gen = MarkdownlintGenerator()
    registry = _registry(
        global_rules={"ruff": {"ignore": ["ANN001"]}},
    )
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    assert "ANN001" not in content


# ---------------------------------------------------------------------------
# check() tests
# ---------------------------------------------------------------------------


def test_markdownlint_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    (tmp_path / ".markdownlint.jsonc").write_text(outputs[Path(".markdownlint.jsonc")])
    issues = gen.check(registry, tmp_path)
    assert issues == []


def test_markdownlint_check_returns_stale_when_missing(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert ".markdownlint.jsonc" in issues[0]


def test_markdownlint_check_returns_stale_when_tampered(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path(".markdownlint.jsonc")]
    (tmp_path / ".markdownlint.jsonc").write_text(content + "\n// TAMPERED")
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert ".markdownlint.jsonc" in issues[0]


def test_markdownlint_check_returns_stale_when_registry_changed(tmp_path: Path) -> None:
    gen = MarkdownlintGenerator()
    registry_old = _registry()
    outputs = gen.generate(registry_old, [], tmp_path)
    (tmp_path / ".markdownlint.jsonc").write_text(outputs[Path(".markdownlint.jsonc")])

    # MD001 is enabled in base; disabling it via registry changes the output
    registry_new = _registry(
        global_rules={"markdownlint": {"ignore": ["MD001"]}},
    )
    issues = gen.check(registry_new, tmp_path)
    assert len(issues) == 1
    assert ".markdownlint.jsonc" in issues[0]


def test_markdownlint_check_stale_message_contains_generate_hint(
    tmp_path: Path,
) -> None:
    gen = MarkdownlintGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert any("ai-guardrails generate" in issue for issue in issues)
