"""Domain models for the support queue example."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


SLA_HOURS_BY_PRIORITY = {
    "urgent": 4,
    "high": 24,
    "medium": 72,
    "low": 120,
}


@dataclass(frozen=True)
class Ticket:
    id: str
    title: str
    status: str
    priority: str
    owner: str
    created_at: datetime

    @classmethod
    def from_dict(cls, raw: dict[str, str]) -> "Ticket":
        return cls(
            id=raw["id"],
            title=raw["title"],
            status=raw["status"],
            priority=raw["priority"],
            owner=raw["owner"],
            created_at=datetime.fromisoformat(raw["created_at"]),
        )

    def sla_due_at(self) -> datetime:
        hours = SLA_HOURS_BY_PRIORITY[self.priority]
        return self.created_at + timedelta(hours=hours)

