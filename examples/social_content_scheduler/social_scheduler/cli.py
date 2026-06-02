"""Command-line interface for the social scheduler example."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .generator import generate_posts
from .poster import post_due
from .scheduler import approve_scheduled_post, calendar_lines, schedule_posts
from .sqlite_store import SQLiteScheduleStore
from .storage import (
    load_brief,
    load_drafts,
    load_receipts,
    load_schedule,
    save_drafts,
    save_receipts,
    save_schedule,
)
from .worker import post_due_from_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate, schedule, and mock-post social content.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate platform-specific post drafts.")
    generate.add_argument("--brief", required=True, help="Path to a campaign brief JSON file.")
    generate.add_argument("--out", required=True, help="Where to write generated drafts JSON.")
    generate.add_argument("--platform", action="append", required=True, help="Platform to generate for.")
    generate.add_argument("--count", type=int, default=3, help="Number of drafts to generate.")

    schedule = subparsers.add_parser("schedule", help="Schedule generated drafts.")
    schedule.add_argument("--drafts", required=True, help="Path to generated drafts JSON.")
    schedule.add_argument("--out", required=True, help="Where to write scheduled posts JSON.")
    schedule.add_argument("--start", required=True, help="ISO timestamp for the first scheduled post.")
    schedule.add_argument("--cadence-hours", type=int, default=24, help="Hours between scheduled posts.")

    approve = subparsers.add_parser("approve", help="Approve a scheduled post by draft id.")
    approve.add_argument("--schedule", required=True, help="Path to scheduled posts JSON.")
    approve.add_argument("--draft-id", required=True, help="Draft id to approve.")
    approve.add_argument("--reviewer", required=True, help="Person or system approving the post.")
    approve.add_argument("--approved-at", required=True, help="ISO timestamp for the approval event.")

    post = subparsers.add_parser("post-due", help="Mock-post scheduled items due at or before --now.")
    post.add_argument("--schedule", required=True, help="Path to scheduled posts JSON.")
    post.add_argument("--outbox", required=True, help="JSONL file where post receipts are appended.")
    post.add_argument("--now", required=True, help="ISO timestamp used as the posting cutoff.")

    calendar = subparsers.add_parser("calendar", help="Print scheduled posts as a compact calendar.")
    calendar.add_argument("--schedule", required=True, help="Path to scheduled posts JSON.")

    db_init = subparsers.add_parser("db-init", help="Create or migrate a SQLite scheduler database.")
    db_init.add_argument("--db", required=True, help="Path to the SQLite database.")

    db_import = subparsers.add_parser("db-import-schedule", help="Import a JSON schedule into SQLite.")
    db_import.add_argument("--db", required=True, help="Path to the SQLite database.")
    db_import.add_argument("--schedule", required=True, help="Path to scheduled posts JSON.")

    db_approve = subparsers.add_parser("db-approve", help="Approve one scheduled post in SQLite.")
    db_approve.add_argument("--db", required=True, help="Path to the SQLite database.")
    db_approve.add_argument("--draft-id", required=True, help="Draft id to approve.")
    db_approve.add_argument("--reviewer", required=True, help="Person or system approving the post.")
    db_approve.add_argument("--approved-at", required=True, help="ISO timestamp for the approval event.")

    db_post = subparsers.add_parser("db-post-due", help="Claim and mock-post due SQLite jobs.")
    db_post.add_argument("--db", required=True, help="Path to the SQLite database.")
    db_post.add_argument("--worker-id", required=True, help="Unique worker id for the job lease.")
    db_post.add_argument("--outbox", required=True, help="Logical outbox destination for receipts.")
    db_post.add_argument("--now", required=True, help="ISO timestamp used as the posting cutoff.")
    db_post.add_argument("--limit", type=int, default=10, help="Maximum due jobs to claim.")

    db_calendar = subparsers.add_parser("db-calendar", help="Print SQLite scheduled posts.")
    db_calendar.add_argument("--db", required=True, help="Path to the SQLite database.")

    return parser


def handle_generate(args: argparse.Namespace) -> int:
    brief = load_brief(Path(args.brief))
    posts = generate_posts(brief, platforms=args.platform, count=args.count)
    save_drafts(Path(args.out), posts)
    print(f"generated={len(posts)} out={args.out}")
    return 0


def handle_schedule(args: argparse.Namespace) -> int:
    drafts = load_drafts(Path(args.drafts))
    scheduled = schedule_posts(
        drafts,
        start_at=datetime.fromisoformat(args.start),
        cadence_hours=args.cadence_hours,
    )
    save_schedule(Path(args.out), scheduled)
    print(f"scheduled={len(scheduled)} out={args.out}")
    return 0


def handle_post_due(args: argparse.Namespace) -> int:
    schedule_path = Path(args.schedule)
    outbox_path = Path(args.outbox)
    scheduled = load_schedule(schedule_path)
    existing = load_receipts(outbox_path)
    updated, receipts = post_due(
        scheduled,
        now=datetime.fromisoformat(args.now),
        outbox_path=outbox_path,
        existing_receipts=existing,
    )
    save_schedule(schedule_path, updated)
    save_receipts(outbox_path, receipts, append=True)
    print(f"posted={len(receipts)} outbox={args.outbox}")
    return 0


def handle_approve(args: argparse.Namespace) -> int:
    schedule_path = Path(args.schedule)
    scheduled = load_schedule(schedule_path)
    updated = approve_scheduled_post(
        scheduled,
        draft_id=args.draft_id,
        reviewer=args.reviewer,
        approved_at=datetime.fromisoformat(args.approved_at),
    )
    save_schedule(schedule_path, updated)
    print(f"approved={args.draft_id} reviewer={args.reviewer}")
    return 0


def handle_calendar(args: argparse.Namespace) -> int:
    scheduled = load_schedule(Path(args.schedule))
    for line in calendar_lines(scheduled):
        print(line)
    return 0


def handle_db_init(args: argparse.Namespace) -> int:
    store = SQLiteScheduleStore(Path(args.db))
    try:
        store.migrate()
    finally:
        store.close()
    print(f"migrated={args.db}")
    return 0


def handle_db_import_schedule(args: argparse.Namespace) -> int:
    store = SQLiteScheduleStore(Path(args.db))
    try:
        store.migrate()
        scheduled = load_schedule(Path(args.schedule))
        store.insert_scheduled(scheduled)
    finally:
        store.close()
    print(f"imported={args.schedule} db={args.db}")
    return 0


def handle_db_approve(args: argparse.Namespace) -> int:
    store = SQLiteScheduleStore(Path(args.db))
    try:
        store.migrate()
        store.approve(
            draft_id=args.draft_id,
            reviewer=args.reviewer,
            approved_at=datetime.fromisoformat(args.approved_at),
        )
    finally:
        store.close()
    print(f"approved={args.draft_id} db={args.db}")
    return 0


def handle_db_post_due(args: argparse.Namespace) -> int:
    store = SQLiteScheduleStore(Path(args.db))
    try:
        store.migrate()
        posted = post_due_from_store(
            store,
            now=datetime.fromisoformat(args.now),
            worker_id=args.worker_id,
            outbox_path=Path(args.outbox),
            limit=args.limit,
        )
    finally:
        store.close()
    print(f"posted={posted} db={args.db}")
    return 0


def handle_db_calendar(args: argparse.Namespace) -> int:
    store = SQLiteScheduleStore(Path(args.db))
    try:
        store.migrate()
        scheduled = store.list_scheduled()
    finally:
        store.close()
    for line in calendar_lines(scheduled):
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return handle_generate(args)
    if args.command == "schedule":
        return handle_schedule(args)
    if args.command == "approve":
        return handle_approve(args)
    if args.command == "post-due":
        return handle_post_due(args)
    if args.command == "calendar":
        return handle_calendar(args)
    if args.command == "db-init":
        return handle_db_init(args)
    if args.command == "db-import-schedule":
        return handle_db_import_schedule(args)
    if args.command == "db-approve":
        return handle_db_approve(args)
    if args.command == "db-post-due":
        return handle_db_post_due(args)
    if args.command == "db-calendar":
        return handle_db_calendar(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
