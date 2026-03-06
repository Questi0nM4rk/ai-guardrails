"""Baseline models — BaselineEntry, BurnDownEntry, and status enum."""

from __future__ import annotations

from dataclasses import dataclass
import datetime
from enum import StrEnum
from typing import Any


class BaselineStatus(StrEnum):
    """Three states for a baseline rule."""

    LEGACY = "legacy"
    BURN_DOWN = "burn_down"
    PROMOTED = "promoted"


@dataclass(frozen=True)
class BaselineEntry:
    """A single fingerprinted issue captured in the baseline snapshot."""

    rule: str
    fingerprint: str
    file: str
    status: BaselineStatus
    captured_at: datetime.date

    @property
    def is_legacy(self) -> bool:
        return self.status == BaselineStatus.LEGACY

    @property
    def is_burn_down(self) -> bool:
        return self.status == BaselineStatus.BURN_DOWN

    @property
    def is_promoted(self) -> bool:
        return self.status == BaselineStatus.PROMOTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "fingerprint": self.fingerprint,
            "file": self.file,
            "status": self.status.value,
            "captured_at": self.captured_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineEntry:
        captured_raw = data["captured_at"]
        captured = (
            datetime.date.fromisoformat(captured_raw)
            if isinstance(captured_raw, str)
            else captured_raw
        )
        return cls(
            rule=data["rule"],
            fingerprint=data["fingerprint"],
            file=data["file"],
            status=BaselineStatus(data["status"]),
            captured_at=captured,
        )


@dataclass(frozen=True)
class BurnDownEntry:
    """Tracks a rule in burn-down mode: declining threshold with deadline."""

    rule: str
    issue_count: int  # count at time of snapshot (current run must not exceed this)
    deadline: datetime.date
    captured_at: datetime.date

    @property
    def deadline_passed(self) -> bool:
        return self.deadline < datetime.datetime.now(tz=datetime.UTC).date()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "issue_count": self.issue_count,
            "deadline": self.deadline.isoformat(),
            "captured_at": self.captured_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BurnDownEntry:
        deadline_raw = data["deadline"]
        deadline = (
            datetime.date.fromisoformat(deadline_raw)
            if isinstance(deadline_raw, str)
            else deadline_raw
        )
        captured_raw = data["captured_at"]
        captured = (
            datetime.date.fromisoformat(captured_raw)
            if isinstance(captured_raw, str)
            else captured_raw
        )
        return cls(
            rule=data["rule"],
            issue_count=data["issue_count"],
            deadline=deadline,
            captured_at=captured,
        )
