# Contributing

## Branching

Do not develop directly on `main`.

Use one branch per Jira issue:

```text
feature/LAN-123-short-description
fix/LAN-124-short-description
refactor/LAN-125-short-description
```

## Commits

Prefer small commits and include the Jira key:

```text
LAN-123 Add scoring model unit tests
```

## Before opening a pull request

Run:

```bash
pytest
ruff check .
```

For broader engine changes also run:

```bash
pytest --cov --cov-report=term-missing
python main.py
```

## Pull requests

A pull request should:

- link the Jira issue;
- describe the behavior changed;
- mention relevant tests;
- avoid unrelated cleanup;
- keep generated files and secrets out of the repository.

## Tests

Test structure:

```text
tests/
├── unit/
├── integration/
├── acceptance/
└── fixtures/
```

Unit tests should avoid external API calls.

Integration and acceptance tests must use frozen fixtures whenever possible.

FACEIT must never be required for CI.

## Code style

Ruff is the initial linting tool.

Do not mass-reformat unrelated files in a functional pull request.

## Objective Engine changes

Any change to scoring weights, normalizers, restrictions or penalties must include tests documenting the new contract.

## Optimizer changes

Changes to FAST, STABLE or GLOBAL must preserve these invariants:

- no player is lost;
- no player is duplicated;
- team sizes remain valid;
- hard structural restrictions remain valid;
- stored score matches independent ObjectiveEngine evaluation;
- GLOBAL never returns a solution worse than its incumbent.
