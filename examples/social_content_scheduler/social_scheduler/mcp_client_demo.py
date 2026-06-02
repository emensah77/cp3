"""Small client that demonstrates the local MCP-style server."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "data" / "brand_brief.json"


def call(proc: subprocess.Popen[str], request: dict) -> dict:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "social_scheduler.mcp_server"],
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
                        "name": "generate_content",
                        "arguments": {
                            "brief_path": str(BRIEF),
                            "output_path": "/tmp/mcp-social-drafts.json",
                            "platforms": ["linkedin", "x"],
                            "count": 2,
                        },
                    },
                },
            )
        )
        print(
            call(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "schedule_content",
                        "arguments": {
                            "drafts_path": "/tmp/mcp-social-drafts.json",
                            "schedule_path": "/tmp/mcp-social-schedule.json",
                            "start": "2026-06-01T09:00:00",
                            "cadence_hours": 6,
                        },
                    },
                },
            )
        )
        print(
            call(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "read_calendar",
                        "arguments": {"schedule_path": "/tmp/mcp-social-schedule.json"},
                    },
                },
            )
        )
    finally:
        proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
