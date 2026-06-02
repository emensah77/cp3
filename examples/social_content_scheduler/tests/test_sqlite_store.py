from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from social_scheduler.generator import generate_posts
from social_scheduler.models import APPROVED, FAILED, POSTED
from social_scheduler.providers import MockSocialProvider
from social_scheduler.scheduler import schedule_posts
from social_scheduler.sqlite_store import SQLiteScheduleStore
from social_scheduler.storage import load_brief
from social_scheduler.worker import post_due_from_store


BRIEF = Path(__file__).resolve().parents[1] / "data" / "brand_brief.json"


def build_schedule(count: int = 2):
    brief = load_brief(BRIEF)
    drafts = generate_posts(brief, platforms=["x"], count=count)
    return schedule_posts(drafts, start_at=datetime(2026, 6, 1, 9), cadence_hours=1)


class SQLiteStoreTests(unittest.TestCase):
    def test_migrate_and_import_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteScheduleStore(Path(tmp) / "scheduler.db")
            try:
                store.migrate()
                store.insert_scheduled(build_schedule(2))

                self.assertEqual(len(store.list_scheduled()), 2)
            finally:
                store.close()

    def test_claim_due_leases_jobs_so_other_workers_do_not_duplicate_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "scheduler.db"
            first = SQLiteScheduleStore(db)
            second = SQLiteScheduleStore(db)
            try:
                first.migrate()
                first.insert_scheduled(build_schedule(2))
                first.approve(draft_id="draft-001", reviewer="casey", approved_at=datetime(2026, 5, 31, 12))
                first.approve(draft_id="draft-002", reviewer="casey", approved_at=datetime(2026, 5, 31, 12))

                first_claim = first.claim_due(
                    now=datetime(2026, 6, 1, 10),
                    worker_id="worker-a",
                    lease_seconds=300,
                    limit=1,
                )
                second_claim = second.claim_due(
                    now=datetime(2026, 6, 1, 10),
                    worker_id="worker-b",
                    lease_seconds=300,
                    limit=10,
                )

                self.assertEqual([item.draft_id for item in first_claim], ["draft-001"])
                self.assertEqual([item.draft_id for item in second_claim], ["draft-002"])
            finally:
                first.close()
                second.close()

    def test_worker_posts_once_and_records_unique_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteScheduleStore(Path(tmp) / "scheduler.db")
            try:
                store.migrate()
                store.insert_scheduled(build_schedule(1))
                store.approve(draft_id="draft-001", reviewer="casey", approved_at=datetime(2026, 5, 31, 12))

                first_count = post_due_from_store(
                    store,
                    now=datetime(2026, 6, 1, 9),
                    worker_id="worker-a",
                    outbox_path=Path(tmp) / "outbox.jsonl",
                )
                second_count = post_due_from_store(
                    store,
                    now=datetime(2026, 6, 1, 9),
                    worker_id="worker-b",
                    outbox_path=Path(tmp) / "outbox.jsonl",
                )

                self.assertEqual(first_count, 1)
                self.assertEqual(second_count, 0)
                self.assertEqual(store.receipt_count(), 1)
                self.assertEqual(store.list_scheduled()[0].status, POSTED)
            finally:
                store.close()

    def test_worker_records_provider_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteScheduleStore(Path(tmp) / "scheduler.db")
            try:
                store.migrate()
                store.insert_scheduled(build_schedule(1))
                store.approve(draft_id="draft-001", reviewer="casey", approved_at=datetime(2026, 5, 31, 12))

                posted = post_due_from_store(
                    store,
                    now=datetime(2026, 6, 1, 9),
                    worker_id="worker-a",
                    outbox_path=Path(tmp) / "outbox.jsonl",
                    provider=MockSocialProvider(fail_platforms={"x"}),
                )

                item = store.list_scheduled()[0]
                self.assertEqual(posted, 0)
                self.assertEqual(item.status, FAILED)
                self.assertIn("mock provider rejected", item.last_error or "")
            finally:
                store.close()

    def test_lease_expiry_allows_reclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "scheduler.db"
            first = SQLiteScheduleStore(db)
            second = SQLiteScheduleStore(db)
            try:
                first.migrate()
                first.insert_scheduled(build_schedule(1))
                first.approve(draft_id="draft-001", reviewer="casey", approved_at=datetime(2026, 5, 31, 12))
                first.claim_due(
                    now=datetime(2026, 6, 1, 9),
                    worker_id="worker-a",
                    lease_seconds=60,
                    limit=1,
                )

                reclaimed = second.claim_due(
                    now=datetime(2026, 6, 1, 9, 1, 1),
                    worker_id="worker-b",
                    lease_seconds=60,
                    limit=1,
                )

                self.assertEqual(reclaimed[0].draft_id, "draft-001")
                self.assertEqual(reclaimed[0].status, APPROVED)
            finally:
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()

