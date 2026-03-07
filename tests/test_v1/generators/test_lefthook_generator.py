"""Tests for LefthookGenerator — tamper-protected lefthook.yml generation."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.generators.lefthook import LefthookGenerator
import yaml

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    parse_hash_header,
)
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


def _parse_body(content: str) -> dict:
    """Strip header line and parse YAML body."""
    body = content.split("\n", 1)[1]
    result = yaml.safe_load(body)
    return result if isinstance(result, dict) else {}


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


def test_lefthook_generator_name() -> None:
    gen = LefthookGenerator()
    assert gen.name == "lefthook"


def test_lefthook_generator_output_files() -> None:
    gen = LefthookGenerator()
    assert gen.output_files == ["lefthook.yml"]


def test_lefthook_generator_produces_hash_header(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("lefthook.yml")]
    assert content.startswith(HASH_HEADER_PREFIX)


def test_lefthook_generator_hash_header_is_valid(tmp_path: Path) -> None:
    """Body hash in header must match the actual body."""
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("lefthook.yml")]
    lines = content.split("\n", 1)
    header_line = lines[0]
    body = lines[1] if len(lines) > 1 else ""
    stored = parse_hash_header(header_line + "\n")
    assert stored == compute_hash(body)


def test_lefthook_generator_produces_valid_yaml(tmp_path: Path) -> None:
    """Body must be valid YAML."""
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("lefthook.yml")]
    body = content.split("\n", 1)[1]
    parsed = yaml.safe_load(body)
    assert isinstance(parsed, dict)


def test_lefthook_generator_has_pre_commit_section(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    parsed = _parse_body(outputs[Path("lefthook.yml")])
    assert "pre-commit" in parsed


def test_lefthook_generator_includes_gitleaks(tmp_path: Path) -> None:
    """gitleaks must always be present regardless of detected languages."""
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    parsed = _parse_body(outputs[Path("lefthook.yml")])
    commands = parsed["pre-commit"]["commands"]
    assert "gitleaks" in commands


def test_lefthook_generator_includes_suppress_comments(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    parsed = _parse_body(outputs[Path("lefthook.yml")])
    commands = parsed["pre-commit"]["commands"]
    assert "suppress-comments" in commands


def test_lefthook_generator_includes_validate_configs(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    parsed = _parse_body(outputs[Path("lefthook.yml")])
    commands = parsed["pre-commit"]["commands"]
    assert "validate-configs" in commands


def test_lefthook_generator_python_adds_ruff(tmp_path: Path) -> None:
    """Python language adds ruff-check and python-format-and-stage hooks."""
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, ["python"], tmp_path)
    parsed = _parse_body(outputs[Path("lefthook.yml")])
    commands = parsed["pre-commit"]["commands"]
    assert "ruff-check" in commands


def test_lefthook_generator_shell_adds_shellcheck(tmp_path: Path) -> None:
    """Shell language adds shellcheck hook."""
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, ["shell"], tmp_path)
    parsed = _parse_body(outputs[Path("lefthook.yml")])
    commands = parsed["pre-commit"]["commands"]
    assert "shellcheck" in commands


def test_lefthook_generator_returns_single_file(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    assert list(outputs.keys()) == [Path("lefthook.yml")]


def test_lefthook_generator_is_deterministic(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    out1 = gen.generate(registry, ["python"], tmp_path)
    out2 = gen.generate(registry, ["python"], tmp_path)
    assert out1[Path("lefthook.yml")] == out2[Path("lefthook.yml")]


# ---------------------------------------------------------------------------
# check() tests
# ---------------------------------------------------------------------------


def test_lefthook_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    (tmp_path / "lefthook.yml").write_text(outputs[Path("lefthook.yml")])
    issues = gen.check(registry, tmp_path)
    assert issues == []


def test_lefthook_check_returns_stale_when_missing(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert "lefthook.yml" in issues[0]


def test_lefthook_check_returns_stale_when_tampered(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("lefthook.yml")]
    (tmp_path / "lefthook.yml").write_text(content + "\n# TAMPERED")
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert "lefthook.yml" in issues[0]


def test_lefthook_check_stale_message_has_generate_hint(tmp_path: Path) -> None:
    gen = LefthookGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert any("ai-guardrails generate" in issue for issue in issues)
