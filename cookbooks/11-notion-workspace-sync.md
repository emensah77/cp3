# Notion Workspace Sync

## Scenario

You want a rigorous Notion cookbook that demonstrates useful automation:
validating a data source schema, mapping local records into Notion page
properties, creating/updating pages idempotently, appending useful blocks, and
exposing the workflow through CLI and MCP-style tools.

## What Exists

The `examples/notion_workspace_sync` project includes:

- A Notion data source schema fixture.
- Project records that sync into Notion pages.
- Connection capability checks for read, insert, and update content.
- Data source sharing checks.
- Schema validation for supported Notion property types.
- Page property payload generation for title, rich text, select, multi-select,
  date, URL, checkbox, and relation-shaped values.
- Block payload generation for summaries and to-do next steps.
- Mock Notion provider with create/update semantics.
- SQLite migrations, leases, audit events, idempotency keys, and sync receipts.
- CLI and MCP-style tools for validation and preview.
- Tests for schema, payloads, provider permissions, leases, idempotency, CLI, and
  MCP.

## Codex Prompt

```text
Extend the Notion workspace sync example with database template support.

Scope:
- Only edit files under examples/notion_workspace_sync.
- Keep Notion behavior mocked; do not add network calls or real credentials.
- Keep the implementation dependency-free.

Feature:
- Add optional `template_id` support to the schema fixture.
- Include template metadata in create-page payloads only when creating a new page.
- Do not include template metadata when updating an existing page.
- Add a CLI command that previews create vs update payload differences.
- Add an MCP tool named preview_notion_upsert_plan.
- Add tests for schema parsing, provider create/update behavior, CLI, and MCP.

Verification:
- Run `PYTHONPATH=examples/notion_workspace_sync python3 -m unittest discover -s examples/notion_workspace_sync/tests`.
```

## Acceptance Criteria

- New pages can include a template reference.
- Existing pages update properties and blocks without re-applying a template.
- Connection insert/update capabilities are still enforced.
- Data source access checks still run before mutation.
- Existing idempotency and lease tests still pass.

## Commands To Start With

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m unittest discover -s examples/notion_workspace_sync/tests
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli validate --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli preview --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli db-init --db /tmp/notion-sync.db
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli import --db /tmp/notion-sync.db --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli sync-due --db /tmp/notion-sync.db --schema examples/notion_workspace_sync/data/notion_schema.json --worker-id worker-a --data-source-id ds-projects
```

## Review Checklist

- Did Codex preserve the mocked-provider safety boundary?
- Are capabilities checked before create or update actions?
- Are page properties shaped according to the schema?
- Are relation values resolved through known page IDs?
- Are create/update differences tested rather than assumed?

## References

- [Notion page properties](https://developers.notion.com/reference/property-value-object)
- [Notion data source properties](https://developers.notion.com/reference/property-object)
- [Notion create page](https://developers.notion.com/reference/post-page)
- [Notion update page](https://developers.notion.com/reference/patch-page)
- [Notion connection capabilities](https://developers.notion.com/reference/capabilities)

