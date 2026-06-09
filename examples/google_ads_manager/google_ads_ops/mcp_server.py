"""Tiny MCP-style JSON-RPC server for Google Ads operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .operation_builder import compile_plan_operations, summarize_operations
from .policy import validate_plan
from .storage import load_plan


TOOLS = [
    {
        "name": "validate_google_ads_plan",
        "description": "Validate campaign plan budgets, domains, and policy text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_path": {"type": "string"},
                "max_daily_budget_micros": {"type": "integer"},
            },
            "required": ["plan_path", "max_daily_budget_micros"],
        },
    },
    {
        "name": "build_google_ads_operations",
        "description": "Compile a campaign plan into concrete Google Ads resource operations.",
        "inputSchema": {
            "type": "object",
            "properties": {"plan_path": {"type": "string"}},
            "required": ["plan_path"],
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
                "serverInfo": {"name": "google-ads-manager", "version": "0.1.0"},
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
    if name == "validate_google_ads_plan":
        plan = load_plan(Path(arguments["plan_path"]))
        violations = validate_plan(
            plan,
            max_daily_budget_micros=int(arguments["max_daily_budget_micros"]),
            allowed_domains={"northstar.example"},
        )
        text = "\n".join(f"{item.mutation_id} {item.code} {item.message}" for item in violations)
        return {"content": [{"type": "text", "text": text or "violations=0"}]}
    if name == "build_google_ads_operations":
        plan = load_plan(Path(arguments["plan_path"]))
        summary = summarize_operations(compile_plan_operations(plan))
        text = "\n".join(f"{key}={summary[key]}" for key in sorted(summary))
        return {"content": [{"type": "text", "text": text}]}
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
