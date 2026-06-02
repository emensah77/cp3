# Expose Tools With MCP

## Scenario

The social scheduler also exposes its workflow as MCP-style tools. This cookbook
shows Codex how to inspect, extend, and test tool-facing code.

## MCP Shape In This Example

The local server in `social_scheduler.mcp_server` supports three JSON-RPC methods:

- `initialize`
- `tools/list`
- `tools/call`

It exposes five tools:

- `generate_content`
- `schedule_content`
- `post_due`
- `approve_content`
- `read_calendar`

This mirrors MCP's tool discovery and invocation flow while staying
dependency-free for the cookbook. OpenAI's MCP docs describe MCP as a standard way
to connect models to tools and context, and the MCP tools concept uses
`tools/list` for discovery and `tools/call` for invocation.

## Codex Prompt

```text
Add an MCP tool to the social_content_scheduler example.

Scope:
- Only edit files under examples/social_content_scheduler.
- Keep the server dependency-free and JSON-RPC based.
- Follow the existing mcp_server.py tool patterns.

Feature:
- Add a `campaign_report` tool that accepts `schedule_path`.
- It should return counts by status and platform.
- It should include the next approved post due, if one exists.
- Add tests for tools/list and tools/call.
- Update examples/social_content_scheduler/README.md with a sample JSON-RPC request.

Verification:
- Run `PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests`.
- Run `PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.mcp_client_demo`.
```

## Manual MCP Smoke Test

Run the demo client:

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.mcp_client_demo
```

Expected behavior:

- The first response initializes the server.
- The second response lists available tools.
- The third response calls `generate_content` and writes `/tmp/mcp-social-drafts.json`.
- Later responses schedule drafts and read the generated calendar.

## Review Checklist

- Did Codex update the tool schema and handler together?
- Does `tools/list` include the new tool?
- Does `tools/call` validate required arguments through normal Python errors?
- Are file writes limited to paths passed by the caller?
- Did tests exercise the MCP-facing behavior, not just internal helpers?

## References

- [OpenAI MCP documentation](https://platform.openai.com/docs/mcp)
- [OpenAI Docs MCP](https://platform.openai.com/docs/docs-mcp)
- [MCP tools concept](https://modelcontextprotocol.io/legacy/concepts/tools)
