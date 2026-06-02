"""Command-line interface for the support queue example."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from .models import Ticket
from .service import load_tickets, summarize_backlog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a support ticket queue.")
    parser.add_argument("--data", required=True, help="Path to a tickets JSON file.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List tickets.")
    list_parser.add_argument(
        "--status",
        choices=["open", "closed"],
        default="open",
        help="Ticket status to show. Defaults to open.",
    )
    list_parser.add_argument(
        "--priority",
        choices=["low", "medium", "high", "urgent"],
        help="Only show tickets at this priority.",
    )

    subparsers.add_parser("summary", help="Show backlog counts.")
    return parser


def format_ticket(ticket: Ticket) -> str:
    due = ticket.sla_due_at().strftime("%Y-%m-%d %H:%M")
    return (
        f"{ticket.id} [{ticket.priority}] {ticket.status} "
        f"owner={ticket.owner} due={due} - {ticket.title}"
    )


def filter_tickets(
    tickets: Iterable[Ticket],
    *,
    status: str | None = None,
    priority: str | None = None,
) -> list[Ticket]:
    result = list(tickets)
    if status is not None:
        result = [ticket for ticket in result if ticket.status == status]
    if priority is not None:
        result = [ticket for ticket in result if ticket.priority == priority]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    tickets = load_tickets(Path(args.data))

    if args.command == "list":
        filtered = filter_tickets(tickets, status=args.status, priority=args.priority)
        for ticket in filtered:
            print(format_ticket(ticket))
        return 0

    if args.command == "summary":
        summary = summarize_backlog(tickets)
        print(f"open={summary['open']} closed={summary['closed']} urgent={summary['urgent']}")
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

