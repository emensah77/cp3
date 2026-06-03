from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from social_scheduler.observability import JsonEventLogger, Metrics
from social_scheduler.permissions import APPROVE, POST, Actor, has_permission, require_permission


class PermissionsAndObservabilityTests(unittest.TestCase):
    def test_role_permissions_are_explicit(self) -> None:
        reviewer = Actor.from_role("casey", "reviewer")
        worker = Actor.from_role("worker-a", "worker")

        self.assertTrue(has_permission(reviewer, APPROVE))
        self.assertFalse(has_permission(reviewer, POST))
        self.assertTrue(has_permission(worker, POST))
        with self.assertRaises(PermissionError):
            require_permission(reviewer, POST)

    def test_metrics_and_json_events_are_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            metrics = Metrics()
            logger = JsonEventLogger(Path(tmp) / "events.jsonl")

            metrics.increment("posts.posted")
            logger.emit(event="post.posted", at=datetime(2026, 6, 1, 9), draft_id="draft-001")

            event = json.loads((Path(tmp) / "events.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(metrics.snapshot(), {"posts.posted": 1})
            self.assertEqual(event["event"], "post.posted")
            self.assertEqual(event["draft_id"], "draft-001")

