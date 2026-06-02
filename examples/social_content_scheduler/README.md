# Social Content Scheduler Example

`social_content_scheduler` is a self-contained example app for demonstrating
Codex on a more product-shaped workflow:

- Generate platform-specific social posts from a brand brief.
- Schedule drafts at a fixed cadence.
- Approve posts before publishing.
- Post due items to a local JSONL outbox.
- Expose the workflow through a tiny MCP-style JSON-RPC server.

The app uses only the Python standard library. Posting is mocked on purpose: this
keeps tests deterministic and prevents accidental real-world publishing.

## Run Tests

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests
```

## Generate Drafts

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli generate --brief examples/social_content_scheduler/data/brand_brief.json --out /tmp/social-drafts.json --platform linkedin --platform x --count 4
```

## Schedule Drafts

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli schedule --drafts /tmp/social-drafts.json --out /tmp/social-schedule.json --start 2026-06-01T09:00:00 --cadence-hours 6
```

Scheduled posts start in `needs_approval` status.

## Approve A Draft

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli approve --schedule /tmp/social-schedule.json --draft-id draft-001 --reviewer casey --approved-at 2026-05-31T12:00:00
```

## Post Due Items

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli post-due --schedule /tmp/social-schedule.json --outbox /tmp/social-outbox.jsonl --now 2026-06-02T12:00:00
```

Only approved, due posts are published. Successful posts are marked `posted` in
the schedule and written to the outbox with an idempotency key. Existing success
receipts prevent duplicate posting on repeated runs.

## SQLite Production Core

The JSON commands are intentionally easy to inspect. The SQLite commands show a
more production-shaped storage path with schema migrations, transactional job
claiming, leases, and unique idempotency receipts.

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-init --db /tmp/social-scheduler.db
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-import-schedule --db /tmp/social-scheduler.db --schedule /tmp/social-schedule.json
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-approve --db /tmp/social-scheduler.db --draft-id draft-001 --reviewer casey --approved-at 2026-05-31T12:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-post-due --db /tmp/social-scheduler.db --worker-id worker-a --outbox /tmp/social-outbox.jsonl --now 2026-06-02T12:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-calendar --db /tmp/social-scheduler.db
```

The SQLite worker claims only approved, due posts whose lease is absent or
expired. Completion inserts a unique receipt by idempotency key and marks the
scheduled item posted in the same transaction.

## Inspect The MCP Server

The MCP server reads newline-delimited JSON-RPC requests from stdin and writes
newline-delimited JSON-RPC responses to stdout. Run the demo client:

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.mcp_client_demo
```

This example mirrors the MCP shape of `initialize`, `tools/list`, and
`tools/call`, while staying dependency-free for cookbook use. The server exposes
`generate_content`, `schedule_content`, `approve_content`, `post_due`, and
`read_calendar`.
