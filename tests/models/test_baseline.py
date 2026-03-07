"""Tests for BaselineEntry, BurnDownEntry, and baseline status enum."""

from __future__ import annotations

import datetime

import pytest

from ai_guardrails.models.baseline import BaselineEntry, BaselineStatus, BurnDownEntry


def test_baseline_status_values():
    assert BaselineStatus.LEGACY == "legacy"
    assert BaselineStatus.BURN_DOWN == "burn_down"
    assert BaselineStatus.PROMOTED == "promoted"


def test_baseline_entry_legacy():
    entry = BaselineEntry(
        rule="ruff/E501",
        fingerprint="abc123def456abcd",
        file="src/cli.py",
        status=BaselineStatus.LEGACY,
        captured_at=datetime.date(2026, 3, 6),
    )
    assert entry.rule == "ruff/E501"
    assert entry.status == BaselineStatus.LEGACY
    assert entry.status == "legacy"
    assert entry.is_legacy
    assert not entry.is_burn_down
    assert not entry.is_promoted


def test_baseline_entry_burn_down():
    entry = BaselineEntry(
        rule="ruff/PLR0913",
        fingerprint="1234567890abcdef",
        file="src/api.py",
        status=BaselineStatus.BURN_DOWN,
        captured_at=datetime.date(2026, 3, 6),
    )
    assert entry.is_burn_down
    assert not entry.is_legacy
    assert not entry.is_promoted


def test_baseline_entry_promoted():
    entry = BaselineEntry(
        rule="ruff/S101",
        fingerprint="fedcba0987654321",
        file="src/tests.py",
        status=BaselineStatus.PROMOTED,
        captured_at=datetime.date(2026, 3, 6),
    )
    assert entry.is_promoted
    assert not entry.is_legacy
    assert not entry.is_burn_down


def test_baseline_entry_is_frozen():
    entry = BaselineEntry(
        rule="ruff/E501",
        fingerprint="abc123def456abcd",
        file="src/cli.py",
        status=BaselineStatus.LEGACY,
        captured_at=datetime.date(2026, 3, 6),
    )
    with pytest.raises(AttributeError):
        entry.status = BaselineStatus.PROMOTED  # type: ignore[misc]


def test_baseline_entry_to_dict():
    entry = BaselineEntry(
        rule="ruff/E501",
        fingerprint="abc123def456abcd",
        file="src/cli.py",
        status=BaselineStatus.LEGACY,
        captured_at=datetime.date(2026, 3, 6),
    )
    d = entry.to_dict()
    assert d["rule"] == "ruff/E501"
    assert d["fingerprint"] == "abc123def456abcd"
    assert d["status"] == "legacy"
    assert d["file"] == "src/cli.py"


def test_baseline_entry_from_dict_round_trip():
    entry = BaselineEntry(
        rule="ruff/E501",
        fingerprint="abc123def456abcd",
        file="src/cli.py",
        status=BaselineStatus.LEGACY,
        captured_at=datetime.date(2026, 3, 6),
    )
    d = entry.to_dict()
    restored = BaselineEntry.from_dict(d)
    assert restored == entry


def test_burn_down_entry_instantiation():
    entry = BurnDownEntry(
        rule="ruff/PLR0913",
        issue_count=23,
        deadline=datetime.date(2026, 9, 1),
        captured_at=datetime.date(2026, 3, 6),
    )
    assert entry.rule == "ruff/PLR0913"
    assert entry.issue_count == 23
    assert entry.deadline == datetime.date(2026, 9, 1)


def test_burn_down_entry_is_frozen():
    entry = BurnDownEntry(
        rule="ruff/PLR0913",
        issue_count=23,
        deadline=datetime.date(2026, 9, 1),
        captured_at=datetime.date(2026, 3, 6),
    )
    with pytest.raises(AttributeError):
        entry.issue_count = 0  # type: ignore[misc]


def test_burn_down_entry_deadline_passed():
    now = datetime.datetime.now(tz=datetime.UTC).date()
    yesterday = now - datetime.timedelta(days=1)
    entry = BurnDownEntry(
        rule="ruff/E501",
        issue_count=5,
        deadline=yesterday,
        captured_at=datetime.date(2026, 1, 1),
    )
    assert entry.deadline_passed


def test_burn_down_entry_deadline_not_passed():
    future = datetime.datetime.now(tz=datetime.UTC).date() + datetime.timedelta(days=30)
    entry = BurnDownEntry(
        rule="ruff/E501",
        issue_count=5,
        deadline=future,
        captured_at=datetime.date(2026, 1, 1),
    )
    assert not entry.deadline_passed


def test_burn_down_entry_to_dict_round_trip():
    entry = BurnDownEntry(
        rule="ruff/PLR0913",
        issue_count=23,
        deadline=datetime.date(2026, 9, 1),
        captured_at=datetime.date(2026, 3, 6),
    )
    d = entry.to_dict()
    restored = BurnDownEntry.from_dict(d)
    assert restored == entry
    assert d["rule"] == "ruff/PLR0913"
    assert d["issue_count"] == 23


def test_baseline_entry_status_comparison():
    """BaselineStatus comparisons work via value."""
    assert BaselineStatus("legacy") == BaselineStatus.LEGACY
    assert BaselineStatus("burn_down") == BaselineStatus.BURN_DOWN
    assert BaselineStatus("promoted") == BaselineStatus.PROMOTED
