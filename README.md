# CS2 Team Balancer

CS2 team-balancing engine for LAN events. Version `0.5.0` is the completed
engine-stabilization baseline: it is an internal, developer-oriented application,
not a mature end-user product or CLI.

The v0.5 baseline includes:

- the production player scoring model;
- `ObjectiveEngine` as the authoritative team-quality evaluation;
- FAST local optimization;
- deterministic STABLE multi-start optimization;
- advanced, bounded GLOBAL search;
- structural optimizer invariants and fresh score reevaluation;
- unit, acceptance, and frozen LAN 2026 regression tests.

## Requirements and installation

- Python >= 3.11
- A FACEIT API key for the default live refresh performed by the application

`pyproject.toml` is the authoritative source for project metadata and
dependencies. Create and activate a virtual environment, then install the project
with its development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Validate a development checkout with:

```powershell
python -m pytest
ruff check .
```

## Application execution

Run the application from the repository root:

```powershell
python main.py
```

In v0.5, optimization mode selection is a developer configuration mechanism in
`main.py`, not a command-line interface. Set the `OPTIMIZATION_MODE` constant to
one of the exact production enum values:

```python
OPTIMIZATION_MODE = OptimizationMode.FAST
OPTIMIZATION_MODE = OptimizationMode.STABLE
OPTIMIZATION_MODE = OptimizationMode.GLOBAL
```

- **FAST** starts from the generated composition and performs local optimization.
- **STABLE** performs deterministic multi-start local optimization and selects a
  reproducible result.
- **GLOBAL** uses a verified STABLE result as its incumbent, builds a
  `GlobalSearchProblem`, runs the bounded `GlobalOptimizer`, reevaluates the
  selected teams with a fresh `ObjectiveEngine` evaluation, and adapts the result
  to `GlobalReportResult` for reporting.

GLOBAL is an advanced bounded-search mode. It can improve or retain the verified
incumbent, but normal node, evaluation, or time limits may stop a run before the
complete search space is exhausted. A normal GLOBAL result therefore does not by
itself prove mathematical optimality. Optimality is proven only when the solver
explicitly establishes it under its admissibility and precondition assumptions.

## Player data and FACEIT

The source roster is `data/players.csv`, with these columns:

```text
Nick,FaceitNickname,Seed,Team
```

`Team` may be empty for automatic optimization. Normal v0.5 execution has
`RUN_FACEIT_IMPORT = True` in `main.py`. It requires `FACEIT_API_KEY`, refreshes
the roster through FACEIT, and writes the enriched runtime data to
`data/players_stats.csv` before balancing. Configure the key in the environment;
never commit credentials or `.env` files:

```powershell
$env:FACEIT_API_KEY="your_key_here"
```

When `RUN_FACEIT_IMPORT = False`, the application does not enrich
`data/players.csv` directly. It reuses an existing `data/players_stats.csv` and
fails with `FileNotFoundError` if that generated file does not exist. The enriched
CSV, FACEIT error CSV, and generated output are ignored by Git.

The test suite is fully offline: it does not call FACEIT and does not require
FACEIT credentials or ignored runtime data. This differs from running the
application with its default live-refresh setting.

## Output

The application writes the HTML report to:

```text
output/lan_report.html
```

Files generated under `output/` are ignored by Git.

## Test architecture

The v0.5.0 release baseline is 408 tests across three layers:

- `tests/unit`: component contracts, scoring and objective behavior, structural
  invariants, moves, neighborhoods, and optimizer behavior.
- `tests/acceptance`: synthetic 20-player FAST/STABLE/GLOBAL cross-component
  behavior and consistency with a fresh `ObjectiveEngine` evaluation.
- `tests/regression`: the reviewed LAN 2026 historical fixture, 20-player power
  fingerprint, deterministic initial generation, and deterministic STABLE
  behavioral fingerprint.

Run the full suite or coverage report with:

```powershell
python -m pytest
python -m pytest --cov --cov-report=term-missing
```

## Project architecture

```text
application/     application facade and report-facing results
evaluation/      internal evaluation models and services
exporters/       HTML reporting
generators/      initial team generation
importers/       player and statistics import
models/          domain models
objective/       authoritative objective engine and restrictions
optimizer/       FAST, STABLE, and GLOBAL optimization
scoring/         individual player scoring
scrapers/        FACEIT data acquisition
tests/unit/      component-level tests
tests/acceptance cross-component engine tests
tests/regression frozen LAN 2026 regression tests
```

## Development workflow

The intended repository workflow is:

```text
Jira issue
  -> feature/SCRUM-16-v05-release-hygiene
  -> development
  -> python -m pytest + ruff check .
  -> pull request
  -> GitHub Actions green
  -> squash merge to main
```

See `CONTRIBUTING.md` and `RELEASE_NOTES.md`.
