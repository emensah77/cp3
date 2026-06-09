# Notion Workspace Sync Example

`notion_workspace_sync` is a rigorous, self-contained Notion operations example.
It demonstrates how to sync local project records into a Notion data source while
staying credential-safe and dependency-free.

The app models:

- Notion connection capabilities and shared data source access.
- Data source schema validation.
- Page property mapping for title, rich text, select, multi-select, date, URL,
  checkbox, and relation-shaped values.
- Idempotent create/update behavior using an external key.
- Page block rendering and append semantics.
- SQLite migrations, leases, audit events, sync receipts, and structured errors.
- MCP-style tools for validation and sync planning.

The provider is mocked by design. A real integration would replace the provider
contract and credential source, not the domain logic.

## Run Tests

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m unittest discover -s examples/notion_workspace_sync/tests
```

## Validate Schema

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli validate --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
```

## Preview Page Payloads

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli preview --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
```

## Sync Through SQLite

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli db-init --db /tmp/notion-sync.db
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli import --db /tmp/notion-sync.db --records examples/notion_workspace_sync/data/projects.json
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli sync-due --db /tmp/notion-sync.db --schema examples/notion_workspace_sync/data/notion_schema.json --worker-id worker-a --data-source-id ds-projects
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli list --db /tmp/notion-sync.db
```

## MCP Demo

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.mcp_client_demo
```

## Official Concepts Mirrored

This example mirrors official Notion API concepts:

- Pages can live as rows inside a data source/database.
- Page properties must conform to their parent data source schema.
- Creating a page requires a page or data source parent.
- Connections have capabilities such as read, insert, and update content.
- Some property types are API-limited, so the example validates supported types.

