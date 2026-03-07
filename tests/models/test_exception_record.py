"""Tests for ExceptionRecord — pending/approved states, TOML round-trip."""

from __future__ import annotations

import datetime

import pytest

from ai_guardrails.models.exception_record import ExceptionRecord


def _make_record(**kwargs: object) -> ExceptionRecord:
    defaults: dict[str, object] = {
        "id": "a1b2c3d4",
        "rule": "ruff/E501",
        "glob": "src/cli.py",
        "reason": "URL cannot be wrapped",
        "proposed_by": "claude-code",
        "approved_by": None,
        "expires": datetime.date(2026, 9, 1),
        "ticket": None,
        "created": datetime.date(2026, 3, 6),
    }
    defaults.update(kwargs)
    return ExceptionRecord(**defaults)  # type: ignore[arg-type]


def test_exception_record_pending():
    record = _make_record(approved_by=None)
    assert record.is_pending
    assert not record.is_approved


def test_exception_record_approved():
    record = _make_record(approved_by="alice")
    assert not record.is_pending
    assert record.is_approved


def test_exception_record_is_frozen():
    record = _make_record()
    with pytest.raises(AttributeError):
        record.reason = "changed"  # type: ignore[misc]


def test_exception_record_with_ticket():
    record = _make_record(ticket="PROJ-42")
    assert record.ticket == "PROJ-42"


def test_exception_record_expired():
    now = datetime.datetime.now(tz=datetime.UTC).date()
    yesterday = now - datetime.timedelta(days=1)
    record = _make_record(expires=yesterday)
    assert record.is_expired


def test_exception_record_not_expired():
    future = datetime.datetime.now(tz=datetime.UTC).date() + datetime.timedelta(days=30)
    record = _make_record(expires=future)
    assert not record.is_expired


def test_exception_record_no_expiry():
    """expires=None means the record never expires."""
    record = _make_record(expires=None)
    assert not record.is_expired


def test_exception_record_to_dict():
    record = _make_record(approved_by="alice", ticket="PROJ-42")
    d = record.to_dict()
    assert d["rule"] == "ruff/E501"
    assert d["approved_by"] == "alice"
    assert d["ticket"] == "PROJ-42"
    assert d["id"] == "a1b2c3d4"


def test_exception_record_from_dict_round_trip():
    record = _make_record(approved_by="alice")
    d = record.to_dict()
    restored = ExceptionRecord.from_dict(d)
    assert restored == record


def test_exception_record_from_dict_pending():
    d = {
        "id": "x1y2z3",
        "rule": "ruff/ARG002",
        "glob": "src/steps/*.py",
        "reason": "Protocol pattern",
        "proposed_by": "cursor",
        "approved_by": None,
        "expires": "2026-12-01",
        "ticket": None,
        "created": "2026-03-06",
    }
    record = ExceptionRecord.from_dict(d)
    assert record.is_pending
    assert record.rule == "ruff/ARG002"
    assert record.expires == datetime.date(2026, 12, 1)


def test_exception_record_generate_id():
    """IDs are deterministic from rule + glob + created."""
    id1 = ExceptionRecord.generate_id(
        "ruff/E501", "src/cli.py", datetime.date(2026, 3, 6)
    )
    id2 = ExceptionRecord.generate_id(
        "ruff/E501", "src/cli.py", datetime.date(2026, 3, 6)
    )
    id3 = ExceptionRecord.generate_id(
        "ruff/E501", "src/api.py", datetime.date(2026, 3, 6)
    )
    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 8  # 8 hex chars


def test_exception_record_all_fields_present():
    record = _make_record(approved_by="bob", ticket="BACK-99")
    assert record.id == "a1b2c3d4"
    assert record.rule == "ruff/E501"
    assert record.glob == "src/cli.py"
    assert record.reason == "URL cannot be wrapped"
    assert record.proposed_by == "claude-code"
    assert record.approved_by == "bob"
    assert record.expires == datetime.date(2026, 9, 1)
    assert record.ticket == "BACK-99"
    assert record.created == datetime.date(2026, 3, 6)
