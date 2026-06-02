from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from support_queue.models import Ticket
from support_queue.service import load_tickets, summarize_backlog, tickets_due_before


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "tickets.json"


class ServiceTests(unittest.TestCase):
    def test_load_tickets_parses_dates(self) -> None:
        tickets = load_tickets(DATA_PATH)

        self.assertEqual(tickets[0].id, "TCK-1001")
        self.assertEqual(tickets[0].created_at, datetime(2026, 5, 28, 9, 0))

    def test_sla_due_at_uses_hours_by_priority(self) -> None:
        urgent = Ticket(
            id="TCK-1",
            title="Example",
            status="open",
            priority="urgent",
            owner="maya",
            created_at=datetime(2026, 5, 30, 8, 15),
        )

        self.assertEqual(urgent.sla_due_at(), datetime(2026, 5, 30, 12, 15))

    def test_tickets_due_before_returns_open_tickets_sorted_for_triage(self) -> None:
        tickets = load_tickets(DATA_PATH)

        due = tickets_due_before(tickets, datetime(2026, 6, 1, 12, 0))

        self.assertEqual([ticket.id for ticket in due], ["TCK-1004", "TCK-1001"])

    def test_summarize_backlog_counts_statuses_and_urgent_open(self) -> None:
        tickets = load_tickets(DATA_PATH)

        self.assertEqual(summarize_backlog(tickets), {"open": 3, "closed": 1, "urgent": 1})


if __name__ == "__main__":
    unittest.main()

