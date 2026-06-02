from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from social_scheduler.mcp_server import handle


ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "data" / "brand_brief.json"


class McpServerTests(unittest.TestCase):
    def test_tools_list_exposes_content_workflow(self) -> None:
        response = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

        tool_names = [tool["name"] for tool in response["result"]["tools"]]
        self.assertEqual(
            tool_names,
            ["generate_content", "schedule_content", "post_due", "approve_content", "read_calendar"],
        )

    def test_generate_content_tool_writes_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "drafts.json"
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_content",
                        "arguments": {
                            "brief_path": str(BRIEF),
                            "output_path": str(output),
                            "platforms": ["x"],
                            "count": 2,
                        },
                    },
                }
            )

            self.assertIn("result", response)
            self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))), 2)

    def test_approval_and_calendar_tools_update_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drafts = Path(tmp) / "drafts.json"
            schedule = Path(tmp) / "schedule.json"
            handle(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "generate_content",
                        "arguments": {
                            "brief_path": str(BRIEF),
                            "output_path": str(drafts),
                            "platforms": ["x"],
                            "count": 1,
                        },
                    },
                }
            )
            handle(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "schedule_content",
                        "arguments": {
                            "drafts_path": str(drafts),
                            "schedule_path": str(schedule),
                            "start": "2026-06-01T09:00:00",
                        },
                    },
                }
            )
            response = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "approve_content",
                        "arguments": {
                            "schedule_path": str(schedule),
                            "draft_id": "draft-001",
                            "reviewer": "casey",
                            "approved_at": "2026-05-31T12:00:00",
                        },
                    },
                }
            )
            calendar = handle(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "read_calendar",
                        "arguments": {"schedule_path": str(schedule)},
                    },
                }
            )

            self.assertIn("result", response)
            self.assertIn("draft-001 approved", calendar["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
