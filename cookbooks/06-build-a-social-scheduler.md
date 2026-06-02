# Build A Social Scheduler

## Scenario

You want a concrete app that Codex can extend end to end: generate social content,
schedule it, approve it, and post due items through a safe mock publisher.

## What Exists

The `examples/social_content_scheduler` project already includes:

- A campaign brief JSON file.
- Deterministic post generation for LinkedIn, X, and Threads.
- A scheduler that spaces posts at a fixed hourly cadence and starts each item in
  `needs_approval`.
- An approval workflow that records reviewer and approval time.
- A mock poster that appends receipts to a JSONL outbox.
- Idempotency keys that prevent duplicate posting when a run is repeated.
- Failed provider attempts that are recorded on the scheduled item and receipt.
- Unit tests using only the Python standard library.

## Codex Prompt

```text
Extend the social_content_scheduler example with a retry workflow for failed posts.

Scope:
- Only edit files under examples/social_content_scheduler.
- Keep posting mocked; do not add real social network APIs.
- Follow the existing standard-library-only style.

Feature:
- Add a CLI command that moves one failed draft back to approved status.
- Reject retry if the draft is not in failed status.
- Preserve the attempt count and clear the last error.
- Add a matching `retry_failed` MCP tool.
- Add tests for CLI, service behavior, and MCP tool behavior.
- Update the example README with the new workflow.

Verification:
- Run `PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests`.
```

## Acceptance Criteria

- Generated drafts, scheduling, approval, and posting still work.
- Failed posts can be retried explicitly.
- Posts cannot be retried while still pending approval, approved, or already posted.
- Existing idempotency behavior is preserved.
- Tests cover both the direct workflow and MCP-facing tool.

## Commands To Start With

```sh
PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli generate --brief examples/social_content_scheduler/data/brand_brief.json --out /tmp/social-drafts.json --platform linkedin --platform x --count 4
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli schedule --drafts /tmp/social-drafts.json --out /tmp/social-schedule.json --start 2026-06-01T09:00:00 --cadence-hours 6
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli approve --schedule /tmp/social-schedule.json --draft-id draft-001 --reviewer casey --approved-at 2026-05-31T12:00:00
PYTHONPATH=examples/social_content_scheduler python3 -m social_scheduler.cli post-due --schedule /tmp/social-schedule.json --outbox /tmp/social-outbox.jsonl --now 2026-06-02T12:00:00
```

## Review Checklist

- Did Codex preserve the local mock-poster safety boundary?
- Did it keep status transitions explicit and testable?
- Did it update tests and docs together?
- Did it preserve idempotency and avoid duplicate outbox writes?
