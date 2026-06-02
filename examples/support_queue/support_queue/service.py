"""Application service functions for the support queue example."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .models import Ticket


def load_tickets(path: Path) -> list[Ticket]:
    raw_tickets = json.loads(path.read_text(encoding="utf-8"))
    return [Ticket.from_dict(raw) for raw in raw_tickets]


def sort_for_triage(tickets: list[Ticket]) -> list[Ticket]:
    priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(tickets, key=lambda ticket: (priority_rank[ticket.priority], ticket.created_at))


def tickets_due_before(tickets: list[Ticket], cutoff: datetime) -> list[Ticket]:
    due = [ticket for ticket in tickets if ticket.status == "open" and ticket.sla_due_at() <= cutoff]
    return sort_for_triage(due)


def summarize_backlog(tickets: list[Ticket]) -> dict[str, int]:
    counts = Counter(ticket.status for ticket in tickets)
    urgent_open = sum(1 for ticket in tickets if ticket.status == "open" and ticket.priority == "urgent")
    return {
        "open": counts["open"],
        "closed": counts["closed"],
        "urgent": urgent_open,
    }

