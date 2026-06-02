from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from social_scheduler.generator import generate_posts
from social_scheduler.models import APPROVED, FAILED, NEEDS_APPROVAL, POSTED
from social_scheduler.poster import post_due
from social_scheduler.providers import MockSocialProvider
from social_scheduler.scheduler import approve_scheduled_post, schedule_posts
from social_scheduler.storage import load_brief


BRIEF = Path(__file__).resolve().parents[1] / "data" / "brand_brief.json"


class SchedulerAndPosterTests(unittest.TestCase):
    def test_schedule_posts_applies_cadence(self) -> None:
        brief = load_brief(BRIEF)
        drafts = generate_posts(brief, platforms=["x"], count=3)

        scheduled = schedule_posts(drafts, start_at=datetime(2026, 6, 1, 9), cadence_hours=8)

        self.assertEqual(
            [item.scheduled_at for item in scheduled],
            [
                datetime(2026, 6, 1, 9),
                datetime(2026, 6, 1, 17),
                datetime(2026, 6, 2, 1),
            ],
        )
        self.assertEqual([item.status for item in scheduled], [NEEDS_APPROVAL, NEEDS_APPROVAL, NEEDS_APPROVAL])

    def test_approve_scheduled_post_updates_exact_match(self) -> None:
        brief = load_brief(BRIEF)
        drafts = generate_posts(brief, platforms=["x"], count=2)
        scheduled = schedule_posts(drafts, start_at=datetime(2026, 6, 1, 9), cadence_hours=8)

        approved = approve_scheduled_post(
            scheduled,
            draft_id="draft-002",
            reviewer="casey",
            approved_at=datetime(2026, 5, 31, 12),
        )

        self.assertEqual(approved[0].status, NEEDS_APPROVAL)
        self.assertEqual(approved[1].status, APPROVED)
        self.assertEqual(approved[1].approved_by, "casey")

    def test_post_due_only_posts_due_approved_items(self) -> None:
        brief = load_brief(BRIEF)
        drafts = generate_posts(brief, platforms=["x"], count=3)
        scheduled = schedule_posts(drafts, start_at=datetime(2026, 6, 1, 9), cadence_hours=8)
        scheduled = approve_scheduled_post(
            scheduled,
            draft_id="draft-001",
            reviewer="casey",
            approved_at=datetime(2026, 5, 31, 12),
        )
        scheduled = approve_scheduled_post(
            scheduled,
            draft_id="draft-002",
            reviewer="casey",
            approved_at=datetime(2026, 5, 31, 12),
        )

        with tempfile.TemporaryDirectory() as tmp:
            updated, receipts = post_due(
                scheduled,
                now=datetime(2026, 6, 1, 17),
                outbox_path=Path(tmp) / "outbox.jsonl",
            )

        self.assertEqual([receipt.draft_id for receipt in receipts], ["draft-001", "draft-002"])
        self.assertEqual([item.status for item in updated], [POSTED, POSTED, NEEDS_APPROVAL])

    def test_post_due_is_idempotent_when_success_receipt_exists(self) -> None:
        brief = load_brief(BRIEF)
        drafts = generate_posts(brief, platforms=["x"], count=1)
        scheduled = schedule_posts(drafts, start_at=datetime(2026, 6, 1, 9), cadence_hours=8)
        scheduled = approve_scheduled_post(
            scheduled,
            draft_id="draft-001",
            reviewer="casey",
            approved_at=datetime(2026, 5, 31, 12),
        )

        with tempfile.TemporaryDirectory() as tmp:
            outbox = Path(tmp) / "outbox.jsonl"
            updated, receipts = post_due(
                scheduled,
                now=datetime(2026, 6, 1, 9),
                outbox_path=outbox,
            )
            second_updated, second_receipts = post_due(
                scheduled,
                now=datetime(2026, 6, 1, 9),
                outbox_path=outbox,
                existing_receipts=receipts,
            )

        self.assertEqual(updated[0].status, POSTED)
        self.assertEqual(second_updated[0].status, POSTED)
        self.assertEqual(second_receipts, [])

    def test_post_due_records_provider_failures(self) -> None:
        brief = load_brief(BRIEF)
        drafts = generate_posts(brief, platforms=["x"], count=1)
        scheduled = schedule_posts(drafts, start_at=datetime(2026, 6, 1, 9), cadence_hours=8)
        scheduled = approve_scheduled_post(
            scheduled,
            draft_id="draft-001",
            reviewer="casey",
            approved_at=datetime(2026, 5, 31, 12),
        )

        with tempfile.TemporaryDirectory() as tmp:
            updated, receipts = post_due(
                scheduled,
                now=datetime(2026, 6, 1, 9),
                outbox_path=Path(tmp) / "outbox.jsonl",
                provider=MockSocialProvider(fail_platforms={"x"}),
            )

        self.assertEqual(updated[0].status, FAILED)
        self.assertEqual(receipts[0].status, FAILED)
        self.assertIn("mock provider rejected", receipts[0].error or "")


if __name__ == "__main__":
    unittest.main()
