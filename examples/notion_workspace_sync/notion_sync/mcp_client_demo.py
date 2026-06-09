"""Demo client for the Notion MCP-style server."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data" / "projects.json"
SCHEMA = ROOT / "data" / "notion_schema.json"


def call(proc: subprocess.Popen[str], request: dict) -> dict:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "notion_sync.mcp_server"],
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
                        "name": "validate_notion_sync",
                        "arguments": {"records_path": str(RECORDS), "schema_path": str(SCHEMA)},
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
                        "name": "preview_notion_pages",
                        "arguments": {"records_path": str(RECORDS), "schema_path": str(SCHEMA)},
                    },
                },
            )
        )
    finally:
        proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

