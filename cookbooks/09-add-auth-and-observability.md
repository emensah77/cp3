# Add Auth And Observability

## Scenario

The scheduler now demonstrates durable state and worker leases. This cookbook
pushes it toward platform engineering: permissions, OAuth-style credential
handling, provider contracts, audit events, metrics, and structured logs.

## What Exists

The `examples/social_content_scheduler` project includes:

- `permissions.py` with role-based permissions for generate, schedule, approve,
  post, and admin operations.
- `credentials.py` with OAuth-style credential metadata and refresh behavior.
- `providers.py` with a provider protocol, registry, and deterministic mock
  provider.
- `observability.py` with metrics counters and JSONL event logging.
- SQLite tables for credentials and audit events.
- Worker tests proving credential refresh, metrics, events, and audit recording.

## Codex Prompt

```text
Harden auth and observability in the social_content_scheduler example.

Scope:
- Only edit files under examples/social_content_scheduler.
- Keep the implementation dependency-free.
- Preserve the safe mock-provider default.

Feature:
- Require RBAC checks in SQLite CLI commands:
  - db-approve requires the reviewer role or admin role.
  - db-post-due requires the worker role or admin role.
- Add --actor-id and --role flags to those commands.
- Record audit events for failed permission checks.
- Add tests for allowed and denied CLI flows.
- Update examples/social_content_scheduler/README.md.

Verification:
- Run `PYTHONPATH=examples/social_content_scheduler python3 -m unittest discover -s examples/social_content_scheduler/tests`.
```

## Acceptance Criteria

- Reviewer can approve.
- Worker can post.
- Marketer cannot approve or post.
- Denied attempts produce audit records.
- Existing worker lease and idempotency tests still pass.
- MCP tool behavior remains unchanged unless explicitly updated.

## Review Checklist

- Are permissions checked before mutating state?
- Are denied operations observable?
- Are role names and permission names centralized?
- Did Codex avoid embedding secrets or real provider tokens?
- Did tests cover both success and failure paths?

