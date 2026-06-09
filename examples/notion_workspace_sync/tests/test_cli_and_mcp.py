from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from notion_sync.cli import main
from notion_sync.mcp_server import handle


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data" / "projects.json"
SCHEMA = ROOT / "data" / "notion_schema.json"


class CliAndMcpTests(unittest.TestCase):
    def test_cli_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "notion.db"

            self.assertEqual(main(["validate", "--records", str(RECORDS), "--schema", str(SCHEMA)]), 0)
            self.assertEqual(main(["preview", "--records", str(RECORDS), "--schema", str(SCHEMA)]), 0)
            self.assertEqual(main(["db-init", "--db", str(db)]), 0)
            self.assertEqual(main(["import", "--db", str(db), "--records", str(RECORDS), "--schema", str(SCHEMA)]), 0)
            self.assertEqual(
                main(
                    [
                        "sync-due",
                        "--db",
                        str(db),
                        "--schema",
                        str(SCHEMA),
                        "--worker-id",
                        "worker-a",
                        "--data-source-id",
                        "ds-projects",
                    ]
                ),
                0,
            )
            self.assertEqual(main(["list", "--db", str(db)]), 0)

    def test_mcp_validate_tool(self) -> None:
        response = handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "validate_notion_sync",
                    "arguments": {"records_path": str(RECORDS), "schema_path": str(SCHEMA)},
                },
            }
        )

        self.assertEqual(response["result"]["content"][0]["text"], "violations=0")

    def test_mcp_preview_tool(self) -> None:
        response = handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "preview_notion_pages",
                    "arguments": {"records_path": str(RECORDS), "schema_path": str(SCHEMA)},
                },
            }
        )

        self.assertIn("proj-001 properties=9 blocks=5", response["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()

