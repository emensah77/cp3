# Add A Tested Feature

## Scenario

The CLI can filter tickets by status and priority. Add support for filtering by
owner so support leads can inspect one teammate's queue.

## Acceptance Criteria

- `PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --owner maya`
  prints `TCK-1001` and does not print `TCK-1002` or `TCK-1004`.
- Owner filtering composes with existing filters.
- Filtering is exact, not substring-based.
- Tests cover the service or CLI behavior.
- Existing tests continue to pass.

## Codex Prompt

```text
Implement owner filtering for the support_queue CLI.

Scope:
- You may edit files under examples/support_queue only.
- Follow the existing CLI and test style.
- Add focused tests for owner filtering.
- Keep owner matching exact.

Acceptance criteria:
- `PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --owner maya`
  shows TCK-1001 and hides TCK-1002 and TCK-1004.
- Owner filtering composes with --status and --priority.
- `PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests` passes.

Before editing, inspect the project and tell me the plan.
```

## Likely Files To Touch

- `examples/support_queue/support_queue/cli.py`
- `examples/support_queue/tests/test_cli.py`

Codex may choose to move filtering into `service.py` if it can justify the extra
abstraction, but the smallest good implementation can stay in `cli.py`.

## Verification

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --owner maya
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --owner maya --priority high
```

## Review Questions

- Did Codex add exact matching rather than `owner in ticket.owner`?
- Did it preserve existing `--status` and `--priority` behavior?
- Did it test the user-visible CLI behavior?
