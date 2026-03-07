"""Tests for RuffGenerator — tamper-protected ruff.toml generation."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.generators.ruff import RuffGenerator

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    parse_hash_header,
)
from ai_guardrails.models.registry import ExceptionRegistry


def _registry(
    *,
    exceptions: list[dict] | None = None,
    file_exceptions: list[dict] | None = None,
    global_rules: dict | None = None,
) -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": global_rules or {},
            "exceptions": exceptions or [],
            "file_exceptions": file_exceptions or [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


def test_ruff_generator_name() -> None:
    gen = RuffGenerator()
    assert gen.name == "ruff"


def test_ruff_generator_output_files() -> None:
    gen = RuffGenerator()
    assert gen.output_files == ["ruff.toml"]


def test_ruff_generator_produces_hash_header(tmp_path: Path) -> None:
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    assert content.startswith(HASH_HEADER_PREFIX)


def test_ruff_generator_hash_header_is_valid(tmp_path: Path) -> None:
    """Body hash must match the header."""
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    lines = content.split("\n", 1)
    header_line = lines[0]
    body = lines[1] if len(lines) > 1 else ""
    stored = parse_hash_header(header_line + "\n")
    assert stored == compute_hash(body)


def test_ruff_generator_contains_base_rules(tmp_path: Path) -> None:
    """Generated ruff.toml must contain target-version and lint select ALL."""
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    assert "target-version" in content
    assert 'select = ["ALL"]' in content


def test_ruff_generator_merges_registry_exceptions(tmp_path: Path) -> None:
    """Registry ruff exceptions must appear in extend-ignore."""
    gen = RuffGenerator()
    registry = _registry(
        global_rules={"ruff": {"ignore": ["ANN001", "ANN201"]}},
    )
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    assert "ANN001" in content
    assert "ANN201" in content


def test_ruff_generator_merges_file_exceptions(tmp_path: Path) -> None:
    """File-scoped registry exceptions must appear in per-file-ignores."""
    gen = RuffGenerator()
    registry = _registry(
        file_exceptions=[
            {
                "glob": "tests/**/*.py",
                "tool": "ruff",
                "rules": ["PLR2004", "S101"],
                "reason": "test files",
            }
        ],
    )
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    assert "tests/**/*.py" in content
    assert "PLR2004" in content
    assert "S101" in content


def test_ruff_generator_no_exceptions_produces_clean_output(tmp_path: Path) -> None:
    """Empty registry still generates a valid ruff.toml."""
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    assert Path("ruff.toml") in outputs
    content = outputs[Path("ruff.toml")]
    assert len(content) > 0


def test_ruff_generator_returns_single_file(tmp_path: Path) -> None:
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    assert list(outputs.keys()) == [Path("ruff.toml")]


def test_ruff_generator_non_ruff_exceptions_ignored(tmp_path: Path) -> None:
    """Exceptions for other tools must not affect ruff output."""
    gen = RuffGenerator()
    registry = _registry(
        global_rules={"markdownlint": {"ignore": ["MD013"]}},
    )
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    assert "MD013" not in content


# ---------------------------------------------------------------------------
# check() tests
# ---------------------------------------------------------------------------


def test_ruff_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    (tmp_path / "ruff.toml").write_text(outputs[Path("ruff.toml")])
    issues = gen.check(registry, tmp_path)
    assert issues == []


def test_ruff_check_returns_stale_when_missing(tmp_path: Path) -> None:
    gen = RuffGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert "ruff.toml" in issues[0]


def test_ruff_check_returns_stale_when_tampered(tmp_path: Path) -> None:
    gen = RuffGenerator()
    registry = _registry()
    outputs = gen.generate(registry, [], tmp_path)
    content = outputs[Path("ruff.toml")]
    # Tamper: append text to body without updating hash
    (tmp_path / "ruff.toml").write_text(content + "\n# TAMPERED")
    issues = gen.check(registry, tmp_path)
    assert len(issues) == 1
    assert "ruff.toml" in issues[0]


def test_ruff_check_returns_stale_when_registry_changed(tmp_path: Path) -> None:
    """File is fresh for old registry but stale when registry gains new exception."""
    gen = RuffGenerator()
    registry_old = _registry()
    outputs = gen.generate(registry_old, [], tmp_path)
    (tmp_path / "ruff.toml").write_text(outputs[Path("ruff.toml")])

    registry_new = _registry(
        global_rules={"ruff": {"ignore": ["ANN001"]}},
    )
    issues = gen.check(registry_new, tmp_path)
    assert len(issues) == 1
    assert "ruff.toml" in issues[0]


def test_ruff_check_stale_message_contains_generate_hint(tmp_path: Path) -> None:
    gen = RuffGenerator()
    registry = _registry()
    issues = gen.check(registry, tmp_path)
    assert any("ai-guardrails generate" in issue for issue in issues)
