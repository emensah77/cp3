from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from google_ads_ops.cli import main
from google_ads_ops.mcp_server import handle


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "campaign_plan.json"
CONVERSIONS = ROOT / "data" / "offline_conversions.json"


class CliAndMcpTests(unittest.TestCase):
    def test_cli_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ads.db"

            self.assertEqual(main(["validate-plan", "--plan", str(PLAN), "--max-daily-budget-micros", "50000000"]), 0)
            self.assertEqual(main(["db-init", "--db", str(db)]), 0)
            self.assertEqual(main(["import-plan", "--db", str(db), "--plan", str(PLAN), "--actor-id", "media-lead"]), 0)
            self.assertEqual(main(["approve", "--db", str(db), "--mutation-id", "mut-001", "--actor-id", "director"]), 0)
            self.assertEqual(
                main(
                    [
                        "sync-approved",
                        "--db",
                        str(db),
                        "--worker-id",
                        "worker-a",
                        "--customer-id",
                        "1234567890",
                        "--login-customer-id",
                        "9998887777",
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "upload-conversions",
                        "--db",
                        str(db),
                        "--conversions",
                        str(CONVERSIONS),
                        "--customer-id",
                        "1234567890",
                        "--debug-enabled",
                    ]
                ),
                0,
            )

    def test_mcp_validate_tool(self) -> None:
        response = handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "validate_google_ads_plan",
                    "arguments": {"plan_path": str(PLAN), "max_daily_budget_micros": 50000000},
                },
            }
        )

        self.assertEqual(response["result"]["content"][0]["text"], "violations=0")

    def test_mcp_tools_list(self) -> None:
        response = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        self.assertEqual(response["result"]["tools"][0]["name"], "validate_google_ads_plan")


if __name__ == "__main__":
    unittest.main()

