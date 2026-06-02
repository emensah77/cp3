"""A tiny MCP-style JSON-RPC server exposing social scheduler tools.

This intentionally implements only the methods needed for the cookbook:
`initialize`, `tools/list`, and `tools/call`.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .generator import generate_posts
from .poster import post_due
from .scheduler import approve_scheduled_post, calendar_lines, schedule_posts
from .storage import (
    load_brief,
    load_drafts,
    load_receipts,
    load_schedule,
    save_drafts,
    save_receipts,
    save_schedule,
)


TOOLS = [
    {
        "name": "generate_content",
        "description": "Generate social post drafts from a campaign brief.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "brief_path": {"type": "string"},
                "output_path": {"type": "string"},
                "platforms": {"type": "array", "items": {"type": "string"}},
                "count": {"type": "integer", "minimum": 1},
            },
            "required": ["brief_path", "output_path", "platforms"],
        },
    },
    {
        "name": "schedule_content",
        "description": "Schedule generated drafts at a fixed hourly cadence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "drafts_path": {"type": "string"},
                "schedule_path": {"type": "string"},
                "start": {"type": "string"},
                "cadence_hours": {"type": "integer", "minimum": 1},
            },
            "required": ["drafts_path", "schedule_path", "start"],
        },
    },
    {
        "name": "post_due",
        "description": "Mock-post due scheduled items to a JSONL outbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schedule_path": {"type": "string"},
                "outbox_path": {"type": "string"},
                "now": {"type": "string"},
            },
            "required": ["schedule_path", "outbox_path", "now"],
        },
    },
    {
        "name": "approve_content",
        "description": "Approve one scheduled post by draft id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schedule_path": {"type": "string"},
                "draft_id": {"type": "string"},
                "reviewer": {"type": "string"},
                "approved_at": {"type": "string"},
            },
            "required": ["schedule_path", "draft_id", "reviewer", "approved_at"],
        },
    },
    {
        "name": "read_calendar",
        "description": "Read scheduled posts as a compact ordered calendar.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schedule_path": {"type": "string"},
            },
            "required": ["schedule_path"],
        },
    },
]


def handle(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    try:
        method = request["method"]
        params = request.get("params", {})
        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "social-content-scheduler", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = call_tool(params["name"], params.get("arguments", {}))
        else:
            raise ValueError(f"Unsupported method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "generate_content":
        brief = load_brief(Path(arguments["brief_path"]))
        posts = generate_posts(
            brief,
            platforms=list(arguments["platforms"]),
            count=int(arguments.get("count", 3)),
        )
        save_drafts(Path(arguments["output_path"]), posts)
        return {"content": [{"type": "text", "text": f"generated {len(posts)} drafts"}]}

    if name == "schedule_content":
        drafts = load_drafts(Path(arguments["drafts_path"]))
        scheduled = schedule_posts(
            drafts,
            start_at=datetime.fromisoformat(arguments["start"]),
            cadence_hours=int(arguments.get("cadence_hours", 24)),
        )
        save_schedule(Path(arguments["schedule_path"]), scheduled)
        return {"content": [{"type": "text", "text": f"scheduled {len(scheduled)} posts"}]}

    if name == "post_due":
        schedule_path = Path(arguments["schedule_path"])
        outbox_path = Path(arguments["outbox_path"])
        scheduled = load_schedule(schedule_path)
        existing = load_receipts(outbox_path)
        updated, receipts = post_due(
            scheduled,
            now=datetime.fromisoformat(arguments["now"]),
            outbox_path=outbox_path,
            existing_receipts=existing,
        )
        save_schedule(schedule_path, updated)
        save_receipts(outbox_path, receipts, append=True)
        return {"content": [{"type": "text", "text": f"posted {len(receipts)} due items"}]}

    if name == "approve_content":
        schedule_path = Path(arguments["schedule_path"])
        scheduled = load_schedule(schedule_path)
        updated = approve_scheduled_post(
            scheduled,
            draft_id=arguments["draft_id"],
            reviewer=arguments["reviewer"],
            approved_at=datetime.fromisoformat(arguments["approved_at"]),
        )
        save_schedule(schedule_path, updated)
        return {"content": [{"type": "text", "text": f"approved {arguments['draft_id']}"}]}

    if name == "read_calendar":
        scheduled = load_schedule(Path(arguments["schedule_path"]))
        text = "\n".join(calendar_lines(scheduled))
        return {"content": [{"type": "text", "text": text}]}

    raise ValueError(f"Unsupported tool: {name}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle(json.loads(line))
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
