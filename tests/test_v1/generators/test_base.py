"""Tests for Generator protocol and hash utilities."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.generators.base import (
    HASH_HEADER_PREFIX,
    compute_hash,
    make_hash_header,
    parse_hash_header,
    verify_hash,
)
from ai_guardrails.models.registry import ExceptionRegistry


def _empty_registry() -> ExceptionRegistry:
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


def test_hash_header_prefix_is_constant() -> None:
    assert HASH_HEADER_PREFIX == "# ai-guardrails:hash:sha256:"


def test_compute_hash_returns_hex_string() -> None:
    digest = compute_hash("hello world")
    assert isinstance(digest, str)
    assert len(digest) == 64  # sha256 hex = 64 chars
    assert all(c in "0123456789abcdef" for c in digest)


def test_compute_hash_is_deterministic() -> None:
    assert compute_hash("foo") == compute_hash("foo")


def test_compute_hash_differs_for_different_content() -> None:
    assert compute_hash("foo") != compute_hash("bar")


def test_make_hash_header_includes_prefix() -> None:
    header = make_hash_header("some content")
    assert header.startswith(HASH_HEADER_PREFIX)


def test_make_hash_header_contains_hash() -> None:
    content = "some content"
    header = make_hash_header(content)
    expected_hash = compute_hash(content)
    assert expected_hash in header


def test_parse_hash_header_extracts_hash() -> None:
    content = "ruff.toml content"
    header = make_hash_header(content)
    text_with_header = header + "\n" + content
    parsed = parse_hash_header(text_with_header)
    assert parsed == compute_hash(content)


def test_parse_hash_header_returns_none_if_missing() -> None:
    assert parse_hash_header("no header here") is None


def test_verify_hash_returns_true_for_matching_content() -> None:
    content = "ruff.toml content"
    header = make_hash_header(content)
    full_text = header + "\n" + content
    assert verify_hash(full_text, content) is True


def test_verify_hash_returns_false_for_tampered_content() -> None:
    content = "ruff.toml content"
    header = make_hash_header(content)
    full_text = header + "\n" + "tampered content"
    assert verify_hash(full_text, "tampered content") is False


def test_verify_hash_returns_false_if_no_header() -> None:
    assert verify_hash("no header", "no header") is False


def test_verify_hash_detects_tampered_body() -> None:
    """Appending to body must be detected even though header hash matches expected."""
    expected_content = "ruff.toml content"
    header = make_hash_header(expected_content)
    # Write original body, then append tamper string
    tampered_body = expected_content + "\nTAMPERED"
    full_text = header + "\n" + tampered_body
    # The stored hash matches expected_content (not tampered_body),
    # so verify_hash must detect the mismatch and return False.
    assert verify_hash(full_text, expected_content) is False


def test_generator_protocol_is_structural() -> None:
    """Ensure Generator can be used as a structural Protocol (not just ABC)."""
    from ai_guardrails.generators.base import Generator

    class _ConcreteGenerator:
        name = "test"
        output_files = ["test.toml"]

        def generate(
            self,
            registry: ExceptionRegistry,
            languages: list[str],
            project_dir: Path,
        ) -> dict[Path, str]:
            return {}

        def check(
            self,
            registry: ExceptionRegistry,
            project_dir: Path,
        ) -> list[str]:
            return []

    # This should not raise — structural subtyping
    gen: Generator = _ConcreteGenerator()  # type: ignore[assignment]
    assert gen.name == "test"
    assert gen.output_files == ["test.toml"]
