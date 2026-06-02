from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from social_scheduler.cli import main


ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "data" / "brand_brief.json"


class CliTests(unittest.TestCase):
    def test_generate_schedule_and_post_due(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drafts = Path(tmp) / "drafts.json"
            schedule = Path(tmp) / "schedule.json"
            outbox = Path(tmp) / "outbox.jsonl"

            self.assertEqual(
                main(
                    [
                        "generate",
                        "--brief",
                        str(BRIEF),
                        "--out",
                        str(drafts),
                        "--platform",
                        "linkedin",
                        "--platform",
                        "x",
                        "--count",
                        "3",
                    ]
                ),
                0,
            )
            self.assertEqual(len(json.loads(drafts.read_text(encoding="utf-8"))), 3)

            self.assertEqual(
                main(
                    [
                        "schedule",
                        "--drafts",
                        str(drafts),
                        "--out",
                        str(schedule),
                        "--start",
                        "2026-06-01T09:00:00",
                        "--cadence-hours",
                        "6",
                    ]
                ),
                0,
            )

            self.assertEqual(
                main(
                    [
                        "approve",
                        "--schedule",
                        str(schedule),
                        "--draft-id",
                        "draft-001",
                        "--reviewer",
                        "casey",
                        "--approved-at",
                        "2026-05-31T12:00:00",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "approve",
                        "--schedule",
                        str(schedule),
                        "--draft-id",
                        "draft-002",
                        "--reviewer",
                        "casey",
                        "--approved-at",
                        "2026-05-31T12:00:00",
                    ]
                ),
                0,
            )

            self.assertEqual(
                main(
                    [
                        "post-due",
                        "--schedule",
                        str(schedule),
                        "--outbox",
                        str(outbox),
                        "--now",
                        "2026-06-01T15:00:00",
                    ]
                ),
                0,
            )
            self.assertEqual(len(outbox.read_text(encoding="utf-8").splitlines()), 2)
            persisted = json.loads(schedule.read_text(encoding="utf-8"))
            self.assertEqual([item["status"] for item in persisted], ["posted", "posted", "needs_approval"])

    def test_calendar_prints_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drafts = Path(tmp) / "drafts.json"
            schedule = Path(tmp) / "schedule.json"
            main(["generate", "--brief", str(BRIEF), "--out", str(drafts), "--platform", "x", "--count", "1"])
            main(["schedule", "--drafts", str(drafts), "--out", str(schedule), "--start", "2026-06-01T09:00:00"])

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["calendar", "--schedule", str(schedule)])

            self.assertEqual(exit_code, 0)
            self.assertIn("2026-06-01T09:00:00 x draft-001 needs_approval", buffer.getvalue())

    def test_sqlite_cli_import_approve_and_post_due(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drafts = Path(tmp) / "drafts.json"
            schedule = Path(tmp) / "schedule.json"
            db = Path(tmp) / "scheduler.db"
            outbox = Path(tmp) / "outbox.jsonl"
            main(["generate", "--brief", str(BRIEF), "--out", str(drafts), "--platform", "x", "--count", "1"])
            main(["schedule", "--drafts", str(drafts), "--out", str(schedule), "--start", "2026-06-01T09:00:00"])

            self.assertEqual(main(["db-init", "--db", str(db)]), 0)
            self.assertEqual(main(["db-import-schedule", "--db", str(db), "--schedule", str(schedule)]), 0)
            self.assertEqual(
                main(
                    [
                        "db-approve",
                        "--db",
                        str(db),
                        "--draft-id",
                        "draft-001",
                        "--reviewer",
                        "casey",
                        "--approved-at",
                        "2026-05-31T12:00:00",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "db-post-due",
                        "--db",
                        str(db),
                        "--worker-id",
                        "worker-a",
                        "--outbox",
                        str(outbox),
                        "--now",
                        "2026-06-01T09:00:00",
                    ]
                ),
                0,
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(["db-calendar", "--db", str(db)])

            self.assertEqual(exit_code, 0)
            self.assertIn("draft-001 posted", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
