"""Generator protocol and shared hash utilities for tamper-protected configs.

All generated configs include a sha256 hash header. The hash covers the
content after the header line, so the header itself is excluded from hashing.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from ai_guardrails.models.registry import ExceptionRegistry

HASH_HEADER_PREFIX = "# ai-guardrails:hash:sha256:"


def compute_hash(content: str) -> str:
    """Return the sha256 hex digest of content (utf-8 encoded)."""
    return hashlib.sha256(content.encode()).hexdigest()


def make_hash_header(content: str) -> str:
    """Return a hash header line for the given content."""
    return f"{HASH_HEADER_PREFIX}{compute_hash(content)}"


def parse_hash_header(text: str) -> str | None:
    """Extract the hash from the first line of text, or None if absent."""
    first_line = text.split("\n", 1)[0].strip()
    if first_line.startswith(HASH_HEADER_PREFIX):
        return first_line[len(HASH_HEADER_PREFIX) :]
    return None


def verify_hash(full_text: str, expected_content: str) -> bool:
    """Return True if the hash header is valid and file has not been tampered.

    Performs two checks:
    1. Tamper check: stored hash must match the actual file body (everything
       after the first line).
    2. Staleness check: stored hash must match the freshly-generated expected
       body.
    """
    stored = parse_hash_header(full_text)
    if stored is None:
        return False
    # Tamper check: stored hash must match actual file body
    lines = full_text.split("\n", 1)
    actual_body = lines[1] if len(lines) > 1 else ""
    if stored != compute_hash(actual_body):
        return False
    # Staleness check: stored hash must match freshly-generated expected body
    return stored == compute_hash(expected_content)


@runtime_checkable
class Generator(Protocol):
    """Protocol that all config generators must satisfy."""

    name: str
    output_files: list[str]

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {relative_path: content} for all files to write."""
        ...

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return list of stale/missing config descriptions (empty = fresh)."""
        ...
