# Onboard A Repo

## Scenario

You are new to the `support_queue` project and want Codex to build a practical
map of the codebase before changing anything.

## Codex Prompt

```text
Explore the support_queue example project and explain how it works.

Scope:
- Only inspect files under examples/support_queue.
- Do not edit files.

Please produce:
- The runtime entry points.
- The main domain objects and service functions.
- The CLI commands and options.
- The test strategy and exact verification command.
- A short data-flow trace for the "list open urgent tickets" workflow.
- 3 safe next tasks for a new contributor.

Use file references in the answer.
```

## Commands Codex Should Discover

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json summary
```

## Expected Observations

- `support_queue.cli` is the command-line entry point.
- `Ticket` is the central domain model.
- `load_tickets`, `tickets_due_before`, and `summarize_backlog` contain service
  behavior.
- Tests use `unittest` and require no external dependencies.
- Ticket data lives in `examples/support_queue/data/tickets.json`.

## Review Checklist

- Did Codex cite concrete files?
- Did it separate facts from assumptions?
- Did it avoid editing files?
- Did it include commands you can actually run?
