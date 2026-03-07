"""ExceptionRecord model — pending/approved exception with full audit trail."""

from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
from typing import Any


@dataclass(frozen=True)
class ExceptionRecord:
    """A single lint exception: proposed by agent, approved by human."""

    id: str
    rule: str
    glob: str
    reason: str
    proposed_by: str
    approved_by: str | None  # None = pending
    expires: datetime.date | None
    ticket: str | None
    created: datetime.date

    @property
    def is_pending(self) -> bool:
        return self.approved_by is None

    @property
    def is_approved(self) -> bool:
        return self.approved_by is not None

    @property
    def is_expired(self) -> bool:
        if self.expires is None:
            return False
        return self.expires < datetime.datetime.now(tz=datetime.UTC).date()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule": self.rule,
            "glob": self.glob,
            "reason": self.reason,
            "proposed_by": self.proposed_by,
            "approved_by": self.approved_by,
            "expires": self.expires.isoformat() if self.expires else None,
            "ticket": self.ticket,
            "created": self.created.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExceptionRecord:
        expires_raw = data.get("expires")
        expires = (
            datetime.date.fromisoformat(expires_raw)
            if isinstance(expires_raw, str)
            else expires_raw
        )
        created_raw = data["created"]
        created = (
            datetime.date.fromisoformat(created_raw)
            if isinstance(created_raw, str)
            else created_raw
        )
        return cls(
            id=data["id"],
            rule=data["rule"],
            glob=data["glob"],
            reason=data["reason"],
            proposed_by=data["proposed_by"],
            approved_by=data.get("approved_by"),
            expires=expires,
            ticket=data.get("ticket"),
            created=created,
        )

    @staticmethod
    def generate_id(rule: str, glob: str, created: datetime.date) -> str:
        """Deterministic 8-char ID from rule + glob + created date."""
        raw = f"{rule}:{glob}:{created.isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:8]
