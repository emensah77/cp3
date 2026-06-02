# Debug A Regression

## Scenario

Someone accidentally changed SLA calculations from hours to days. Codex should
reproduce the failing test, find the root cause, patch the bug, and verify the fix.

## Setup

Apply the regression patch:

```sh
git apply examples/support_queue/patches/03-sla-regression.patch
```

Confirm the failure:

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
```

## Codex Prompt

```text
Debug the failing support_queue tests.

Scope:
- Only edit files under examples/support_queue.
- Reproduce the failure first.
- Identify the smallest root cause.
- Patch the bug without broad refactors.
- Re-run `PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests`.

Finish with:
- The failing assertion.
- The root cause.
- The files changed.
- The verification result.
```

## Expected Root Cause

`Ticket.sla_due_at()` should add SLA values as hours. The regression changed the
calculation to days, causing urgent tickets to be due far too late.

## Likely File To Touch

- `examples/support_queue/support_queue/models.py`

## Cleanup

After the exercise, the working tree should contain the fixed code. If you want to
reset the exercise manually, inspect the diff and restore the intended
`timedelta(hours=hours)` behavior.
