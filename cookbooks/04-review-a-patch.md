# Review A Patch

## Scenario

A teammate submitted an owner-filter patch. It looks plausible, but the matching
logic may be wrong and there may be missing tests. Use Codex as a review assistant.

## Setup

Apply the sample patch:

```sh
git apply examples/support_queue/patches/04-risky-owner-filter.patch
```

## Codex Prompt

```text
Review the current support_queue changes as if this were a pull request.

Focus on:
- Bugs or behavior changes.
- Missing tests.
- Incorrect assumptions about matching, filtering, or CLI behavior.

Please:
- Inspect the diff and surrounding code.
- Lead with findings ordered by severity.
- Include file and line references.
- Keep style comments out unless they affect correctness.
- Do not edit files yet.
```

## Expected Finding

The patch uses substring owner matching:

```python
owner in ticket.owner
```

That can return the wrong tickets. For example, `--owner ay` would match `maya`.
The acceptance criteria for the feature require exact matching.

## Strong Follow-Up

```text
Now fix only the confirmed owner-filter review findings and add the smallest useful tests.
```

## Verification

```sh
PYTHONPATH=examples/support_queue python3 -m unittest discover -s examples/support_queue/tests
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --owner ay
PYTHONPATH=examples/support_queue python3 -m support_queue.cli --data examples/support_queue/data/tickets.json list --owner maya
```

## Review Checklist

- Did Codex identify the substring-matching bug?
- Did it ask for or add tests that catch the bug?
- Did it avoid unrelated refactors?
