# Productionize The Scheduler Core

## Scenario

The social scheduler has a safe local JSON workflow, but production systems need
durable storage, migrations, transactions, and worker coordination. This cookbook
uses the SQLite-backed core to teach those patterns without requiring cloud
infrastructure.

## What Exists

The `examples/social_content_scheduler` project includes:

- `SQLiteScheduleStore` with schema migrations.
- A `scheduled_posts` table with status, approval metadata, attempts, errors,
  idempotency key, and lease fields.
- A `post_receipts` table with a unique idempotency key.
- A worker helper that claims due posts, publishes through a mock provider, and
  completes or fails jobs.
- Tests proving leases, idempotency, failure recording, and CLI integration.

## Codex Prompt

```text
Harden the SQLite production core for the social_content_scheduler example.

Scope:
- Only edit files under examples/social_content_scheduler.
- Keep the implementation dependency-free.
- Preserve the JSON workflow and existing MCP tools.

Feature:
- Add a retry command for failed SQLite posts.
- It should move exactly one failed draft back to approved status.
- It must preserve attempts and clear last_error.
- It must reject drafts that are needs_approval, approved, or posted.
- Add a matching MCP tool named retry_failed.
- Add tests for store behavior, CLI behavior, and MCP behavior.

Verification:
- Run `PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests`.
```

## Acceptance Criteria

- Migrations still run on an empty database.
- Two workers cannot claim the same leased post at the same time.
- A repeated worker run cannot create duplicate success receipts.
- Failed posts can be retried explicitly.
- Non-failed posts cannot be retried.
- Existing JSON commands still pass their tests.

## Commands To Start With

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-init --db /tmp/social-scheduler.db
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli generate --brief examples/social_content_scheduler/data/brand_brief.json --out /tmp/social-drafts.json --platform x --count 1
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli schedule --drafts /tmp/social-drafts.json --out /tmp/social-schedule.json --start 2026-06-01T09:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-import-schedule --db /tmp/social-scheduler.db --schedule /tmp/social-schedule.json
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-approve --db /tmp/social-scheduler.db --draft-id draft-001 --reviewer casey --approved-at 2026-05-31T12:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli db-post-due --db /tmp/social-scheduler.db --worker-id worker-a --outbox /tmp/social-outbox.jsonl --now 2026-06-01T09:00:00
```

## Review Checklist

- Did Codex keep retry as an explicit state transition?
- Did it avoid resetting attempt count?
- Did tests prove invalid retry states are rejected?
- Did MCP tool schema, handler, and tests change together?
- Did the implementation preserve idempotent posting and lease behavior?

