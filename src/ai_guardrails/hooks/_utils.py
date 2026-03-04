"""Shared utilities for hook modules."""

from __future__ import annotations

from pathlib import Path

_HASH_PREFIX = "ai-guardrails:hash:sha256:"
_HEADER_SCAN_LINES = 5


def has_hash_header(filepath: str) -> bool:
    """Return True if the file has an ai-guardrails hash header near the top."""
    try:
        with Path(filepath).open(encoding="utf-8", errors="replace") as f:
            for _ in range(_HEADER_SCAN_LINES):
                line = f.readline()
                if not line:
                    break
                if _HASH_PREFIX in line:
                    return True
    except OSError:
        pass
    return False
