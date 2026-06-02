# Support Queue Example

`support_queue` is a tiny Python project used by the Codex cookbooks. It models a
customer support queue, including ticket loading, filtering, SLA calculations, and
a small command-line interface.

Run tests from the repository root:

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
```

List open tickets:

```sh
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list
```

Show a backlog summary:

```sh
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json summary
```

The project intentionally stays dependency-free so Codex can run it in a fresh
workspace without setup.
