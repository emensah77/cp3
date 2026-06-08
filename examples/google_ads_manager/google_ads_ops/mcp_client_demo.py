"""Demo client for the Google Ads MCP-style server."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "data" / "campaign_plan.json"


def call(proc: subprocess.Popen[str], request: dict) -> dict:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "google_ads_ops.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        print(call(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}))
        print(call(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}))
        print(
            call(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "validate_google_ads_plan",
                        "arguments": {
                            "plan_path": str(PLAN),
                            "max_daily_budget_micros": 50000000,
                        },
                    },
                },
            )
        )
    finally:
        proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

