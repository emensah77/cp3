# Google Ads Operations

## Scenario

You want a highly rigorous Codex cookbook for Google Ads automation without any
risk of real ad spend. This example models campaign mutation workflows and
offline conversion uploads with production-shaped guardrails, all through a mock
provider.

## What Exists

The `examples/google_ads_manager` project includes:

- Campaign plan validation with budget, URL, channel, duplicate-id, and policy
  checks.
- Google Ads credential metadata with developer token, OAuth token fields,
  target customer ID, and optional login customer ID.
- A mock provider that mirrors validate-only, partial-failure, request-id,
  mutation receipt, and offline conversion upload behavior.
- SQLite migrations, leases, audit events, idempotency keys, and unique receipts.
- Conversion upload handling with debug behavior, consent checks, and
  per-conversion errors.
- MCP-style tooling for campaign plan validation.
- Tests for policy, credentials, provider behavior, CLI, MCP, leases,
  idempotency, and conversion uploads.

## Codex Prompt

```text
Extend the Google Ads operations example with budget-change approval limits.

Scope:
- Only edit files under examples/google_ads_manager.
- Keep all Google Ads API behavior mocked.
- Do not add network calls or real credentials.
- Keep the implementation dependency-free.

Feature:
- Add a policy rule that blocks budget increases greater than 25% over the
  currently stored budget for the same campaign.
- Store the previous approved budget in SQLite.
- Add a CLI command that previews budget deltas before approval.
- Add an MCP tool named preview_budget_deltas.
- Add tests for allowed increases, blocked increases, CLI output, and MCP output.

Verification:
- Run `PYTHONPATH=examples/google_ads_manager python3 -m unittest discover -s examples/google_ads_manager/tests`.
```

## Acceptance Criteria

- Budget deltas are calculated in micros.
- The policy compares against the last approved stored budget, not the incoming
  plan alone.
- A campaign with no prior approved budget can still be imported and reviewed.
- Blocked budget increases do not change approval state.
- Existing mutation sync and conversion upload tests still pass.

## Commands To Start With

```sh
PYTHONPATH=examples/google_ads_manager python3 -m unittest discover -s examples/google_ads_manager/tests
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli validate-plan --plan examples/google_ads_manager/data/campaign_plan.json --max-daily-budget-micros 50000000
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli db-init --db /tmp/google-ads-ops.db
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli import-plan --db /tmp/google-ads-ops.db --plan examples/google_ads_manager/data/campaign_plan.json --actor-id media-lead
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli approve --db /tmp/google-ads-ops.db --mutation-id mut-001 --actor-id director
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli sync-approved --db /tmp/google-ads-ops.db --worker-id worker-a --customer-id 1234567890 --login-customer-id 9998887777
PYTHONPATH=examples/google_ads_manager python3 -m google_ads_ops.cli upload-conversions --db /tmp/google-ads-ops.db --conversions examples/google_ads_manager/data/offline_conversions.json --customer-id 1234567890 --debug-enabled
```

## Review Checklist

- Did Codex preserve the no-real-spend safety boundary?
- Are developer token and OAuth values treated as metadata, not printed raw?
- Are partial-failure and validate-only semantics preserved?
- Are budget approvals transactional and auditable?
- Do tests prove idempotency for both campaign mutations and conversion uploads?

## References

- [Google Ads API partial failures](https://developers.google.com/google-ads/api/docs/best-practices/partial-failures)
- [Google Ads API mutate requests](https://developers.google.com/google-ads/api/rest/common/mutate)
- [Google Ads offline click conversions](https://developers.google.com/google-ads/api/docs/conversions/upload-clicks)
- [Google Ads API authorization and headers](https://developers.google.com/google-ads/api/rest/auth)

