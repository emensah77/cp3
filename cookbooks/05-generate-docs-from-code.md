# Generate Docs From Code

## Scenario

The example project has a minimal README, but it does not fully document the CLI
behavior. Ask Codex to update documentation from the implementation and tests.

## Acceptance Criteria

- The README documents both CLI commands.
- The README lists supported `list` filters.
- Commands are copy-pasteable from the repository root.
- The docs do not mention features that are not implemented.
- Tests still pass.

## Codex Prompt

```text
Update examples/support_queue/README.md so it accurately documents the CLI.

Scope:
- Treat source code and tests under examples/support_queue as the source of truth.
- Do not invent behavior that is not implemented.
- Include copy-pasteable commands from the repository root.
- Document the list and summary commands.
- Document supported filters for list.
- Run `PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests`.

Before editing, inspect the CLI parser and tests.
```

## Likely Files To Touch

- `examples/support_queue/README.md`

## Verification

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --priority urgent
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json summary
```

## Review Questions

- Did Codex document only implemented flags?
- Are examples rooted at the repository root?
- Did it preserve the simple setup story with no external dependencies?
