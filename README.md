# Codex Cookbooks

Hands-on cookbooks that demonstrate how to use Codex on real engineering work.

This repository includes three runnable Python projects:

- `support_queue`: a compact ticket queue used for everyday coding workflows.
- `social_content_scheduler`: a local-first content generator, scheduler, mock
  poster, and MCP tool server.
- `google_ads_manager`: a highly rigorous Google Ads operations example with
  mocked campaign mutation and offline conversion workflows.
- `notion_workspace_sync`: a Notion data source/page sync example with schema
  validation, capabilities, idempotency, leases, CLI, and MCP tools.

Each cookbook gives Codex a concrete task, with acceptance criteria, commands to
run, expected files to touch, and review questions.

## Quickstart

Run the sample project tests:

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
```

Try the CLI:

```sh
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json summary
```

Run the social content scheduler:

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli generate --brief examples/social_content_scheduler/data/brand_brief.json --out /tmp/social-drafts.json --platform linkedin --platform x --count 4
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli schedule --drafts /tmp/social-drafts.json --out /tmp/social-schedule.json --start 2026-06-01T09:00:00 --cadence-hours 6
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli approve --schedule /tmp/social-schedule.json --draft-id draft-001 --reviewer casey --approved-at 2026-05-31T12:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli post-due --schedule /tmp/social-schedule.json --outbox /tmp/social-outbox.jsonl --now 2026-06-02T12:00:00
```

Try the SQLite-backed production core:

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-init --db /tmp/social-scheduler.db
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-import-schedule --db /tmp/social-scheduler.db --schedule /tmp/social-schedule.json
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-approve --db /tmp/social-scheduler.db --draft-id draft-001 --reviewer casey --approved-at 2026-05-31T12:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-post-due --db /tmp/social-scheduler.db --worker-id worker-a --outbox /tmp/social-outbox.jsonl --now 2026-06-02T12:00:00
```

Run the Google Ads operations example:

```sh
PYTHONPATH=examples/google_ads_manager python3 -m unittest discover -s examples/google_ads_manager/tests
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli validate-plan --plan examples/google_ads_manager/data/campaign_plan.json --max-daily-budget-micros 50000000
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli build-operations --plan examples/google_ads_manager/data/campaign_plan.json
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli db-init --db /tmp/google-ads-ops.db
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli import-plan --db /tmp/google-ads-ops.db --plan examples/google_ads_manager/data/campaign_plan.json --actor-id media-lead
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli approve --db /tmp/google-ads-ops.db --mutation-id mut-001 --actor-id director
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli sync-approved --db /tmp/google-ads-ops.db --worker-id worker-a --customer-id 1234567890 --login-customer-id 9998887777
```

Run the Notion workspace sync example:

```sh
PYTHONPATH=examples/notion_workspace_sync python3 -m unittest discover -s examples/notion_workspace_sync/tests
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli validate --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.cli preview --records examples/notion_workspace_sync/data/projects.json --schema examples/notion_workspace_sync/data/notion_schema.json
PYTHONPATH=examples/notion_workspace_sync python3 -m notion_sync.mcp_client_demo
```

## Cookbooks

| Cookbook | Codex capability | Concrete outcome |
| --- | --- | --- |
| [01 Onboard A Repo](cookbooks/01-onboard-a-repo.md) | Repository exploration and architecture synthesis | Codex produces a file-referenced architecture note for `support_queue`. |
| [02 Add A Tested Feature](cookbooks/02-add-a-tested-feature.md) | Scoped implementation with tests | Codex adds owner filtering to the service and CLI. |
| [03 Debug A Regression](cookbooks/03-debug-a-regression.md) | Failure reproduction and root-cause analysis | Codex fixes a deliberately introduced SLA regression. |
| [04 Review A Patch](cookbooks/04-review-a-patch.md) | Pull-request review | Codex reviews a risky diff and proposes targeted fixes. |
| [05 Generate Docs From Code](cookbooks/05-generate-docs-from-code.md) | Documentation grounded in implementation | Codex writes accurate CLI docs from source and tests. |
| [06 Build A Social Scheduler](cookbooks/06-build-a-social-scheduler.md) | End-to-end product work | Codex extends an approval-gated, idempotent content scheduler. |
| [07 Expose Tools With MCP](cookbooks/07-expose-tools-with-mcp.md) | MCP tool design and testing | Codex adds or reviews tools on a local MCP-style server. |
| [08 Productionize The Scheduler Core](cookbooks/08-productionize-the-scheduler-core.md) | Production engineering patterns | Codex works with SQLite migrations, leases, and idempotent workers. |
| [09 Add Auth And Observability](cookbooks/09-add-auth-and-observability.md) | Production platform concerns | Codex extends RBAC, OAuth-style credentials, audit logs, metrics, and provider contracts. |
| [10 Google Ads Operations](cookbooks/10-google-ads-operations.md) | Ads automation engineering | Codex extends safe campaign, ad group, RSA, keyword, mutation, and conversion workflows. |
| [11 Notion Workspace Sync](cookbooks/11-notion-workspace-sync.md) | Notion API engineering | Codex extends safe data source schema, page upsert, block, lease, and MCP workflows. |

## Repository Layout

```text
examples/support_queue/
  data/tickets.json              # Sample ticket data
  support_queue/                 # Small Python package
  tests/                         # Unit tests using the standard library
  patches/                       # Optional exercise patches

examples/social_content_scheduler/
  data/brand_brief.json           # Campaign input
  social_scheduler/               # Generator, scheduler, poster, MCP server
  tests/                          # Unit tests using the standard library

examples/google_ads_manager/
  data/campaign_plan.json          # Campaign mutation input
  data/offline_conversions.json    # Offline conversion input
  google_ads_ops/                  # Policy, provider, SQLite, CLI, MCP
  tests/                           # Unit tests using the standard library

examples/notion_workspace_sync/
  data/notion_schema.json           # Data source schema fixture
  data/projects.json                # Project records to sync
  notion_sync/                      # Schema, payloads, provider, SQLite, CLI, MCP
  tests/                            # Unit tests using the standard library

cookbooks/
  01-onboard-a-repo.md
  02-add-a-tested-feature.md
  03-debug-a-regression.md
  04-review-a-patch.md
  05-generate-docs-from-code.md
  06-build-a-social-scheduler.md
  07-expose-tools-with-mcp.md
  08-productionize-the-scheduler-core.md
  09-add-auth-and-observability.md
  10-google-ads-operations.md
  11-notion-workspace-sync.md
```

## What Makes These Robust

- Every cookbook starts from the same runnable project.
- Each task has explicit acceptance criteria.
- Verification uses standard-library Python commands, so no dependency install is
  required.
- Cookbooks tell Codex what it may edit and what it should leave alone.
- Review prompts ask for file and line references instead of broad impressions.
- The flagship scheduler includes production-shaped interfaces for permissions,
  credentials, provider adapters, audit events, metrics, leases, and idempotency.
- The Google Ads example mirrors high-risk ads automation concerns while keeping
  all API calls mocked and safe by default.
- The Notion example mirrors real data source/page workflows while keeping
  workspace access mocked and safe by default.
