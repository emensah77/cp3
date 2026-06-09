"""Tiny MCP-style JSON-RPC server for Notion sync tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .payloads import build_page_payload
from .schema import validate_records
from .storage import load_records, load_schema


TOOLS = [
    {
        "name": "validate_notion_sync",
        "description": "Validate project records against a Notion data source schema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records_path": {"type": "string"},
                "schema_path": {"type": "string"},
            },
            "required": ["records_path", "schema_path"],
        },
    },
    {
        "name": "preview_notion_pages",
        "description": "Preview Notion page property/block payload counts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records_path": {"type": "string"},
                "schema_path": {"type": "string"},
            },
            "required": ["records_path", "schema_path"],
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
                "serverInfo": {"name": "notion-workspace-sync", "version": "0.1.0"},
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
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    records = load_records(Path(arguments["records_path"]))
    schema = load_schema(Path(arguments["schema_path"]))
    if name == "validate_notion_sync":
        violations = validate_records(records, schema)
        text = "\n".join(f"{item.external_id} {item.code} {item.message}" for item in violations)
        return {"content": [{"type": "text", "text": text or "violations=0"}]}
    if name == "preview_notion_pages":
        lines = []
        for record in records:
            payload = build_page_payload(record, schema)
            lines.append(f"{record.external_id} properties={len(payload['properties'])} blocks={len(payload['children'])}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}
    raise ValueError(f"Unsupported tool: {name}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        sys.stdout.write(json.dumps(handle(json.loads(line))) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

