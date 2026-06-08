# Google Ads Manager Example

`google_ads_manager` is a rigorous, self-contained Google Ads operations example.
It demonstrates production-shaped advertising automation without touching a real
Google Ads account or spending money.

The app models:

- Campaign plan validation before mutation.
- Budget and policy guardrails.
- Approval-gated campaign changes.
- Validate-only and partial-failure style API behavior.
- Idempotent campaign mutations.
- Offline click conversion uploads with consent and debug handling.
- Developer-token, OAuth, customer ID, and login-customer ID metadata.
- SQLite migrations, leases, audit events, metrics, and MCP-style tools.

The mock provider is intentionally deterministic. Real Google Ads integration
would replace the provider contract and credential source, not the domain model.

## Run Tests

```sh
PYTHONPATH=examples/google_ads_manager python3 -m unittest discover -s examples/google_ads_manager/tests
```

## Validate A Campaign Plan

```sh
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli validate-plan --plan examples/google_ads_manager/data/campaign_plan.json --max-daily-budget-micros 50000000
```

## Import, Approve, And Sync Mutations

```sh
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli db-init --db /tmp/google-ads-ops.db
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli import-plan --db /tmp/google-ads-ops.db --plan examples/google_ads_manager/data/campaign_plan.json --actor-id media-lead
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli approve --db /tmp/google-ads-ops.db --mutation-id mut-001 --actor-id director
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli sync-approved --db /tmp/google-ads-ops.db --worker-id worker-a --customer-id 1234567890 --login-customer-id 9998887777
```

## Upload Offline Conversions

```sh
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli upload-conversions --db /tmp/google-ads-ops.db --conversions examples/google_ads_manager/data/offline_conversions.json --customer-id 1234567890 --debug-enabled
```

## MCP Demo

```sh
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.mcp_client_demo
```

## Official Concepts Mirrored

This example mirrors concepts from official Google Ads API documentation:

- Mutate requests can support validate-only and partial-failure style workflows.
- API calls require OAuth credentials and a developer token; manager-account
  flows can include a login customer ID.
- Offline click conversion uploads include consent/debug behavior and can return
  per-conversion errors.

