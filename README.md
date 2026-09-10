# CS2 Team Balancer

CS2 tools for LAN events. The current release is `0.6.0`, with two main
capabilities: **LAN Team Balancing** and **LAN Tournament Analytics & Reporting**.
Version `0.5.0` established the engine-stabilization baseline; v0.6.0 adds the
complete tournament analytics pipeline implemented under SCRUM-17, from map CSV
imports to a standalone HTML report.

The application remains developer-oriented and has no mature public CLI.
Balancing runs through `main.py`; tournament reporting uses the public Python API
shown below.

## LAN Team Balancing

The balancing engine retains the v0.5 baseline capabilities:

- the production player scoring model;
- `ObjectiveEngine` as the authoritative team-quality evaluation;
- FAST local optimization;
- deterministic STABLE multi-start optimization;
- advanced, bounded GLOBAL search;
- structural optimizer invariants and fresh score reevaluation;
- unit, acceptance, and frozen LAN 2026 regression tests.

## Requirements and installation

- Python >= 3.11
- A FACEIT API key for the default live refresh in the balancing application
  (the tournament CSV-to-report flow does not require FACEIT)

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

## Balancing application execution

Run the application from the repository root:

```powershell
python main.py
```

Optimization mode selection is a developer configuration mechanism in
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

`Team` may be empty for automatic optimization. Default balancing execution has
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

## Balancing output

The application writes the HTML report to:

```text
output/lan_report.html
```

Files generated under `output/` are ignored by Git.

## Tournament analytics

The LAN Tournament Analytics & Reporting pipeline is:

```text
Tournament folder
    ↓
Series folders
    ↓
Map CSV files
    ↓
Validation + deduplication
    ↓
Statistics aggregation
    ↓
Player Impact Rating v1
    ↓
Deterministic rankings / MVP
    ↓
Merit titles
    ↓
Standalone HTML tournament report
```

Each direct child folder of the tournament represents a series; its immediate
CSV files represent played maps. Root-level CSVs and nested directories are
ignored. For example:

```text
tournament/
  group-a/
    map-0.csv
  semifinal/
    map-0.csv
    map-1.csv
  final/
    map-0.csv
    map-1.csv
    map-2.csv
```

The folder defines the series boundary, **not `matchid`**. Supply `BestOf`
explicitly as metadata keyed by the exact folder name, using `BestOf` enum
values. BO1/BO3/BO5 must never be inferred by counting CSVs: a series can have
fewer played maps than its BestOf limit without proving completion or an outcome.

`steamid64` is the canonical player identity across maps, series, and the
tournament. Nicknames are presentation data and may change; aggregation retains
aliases without splitting the player into separate identities.

The importer supports diagnostics and partial success: invalid CSVs are reported
while valid maps remain available. Exact duplicates of parsed map data are
skipped tournament-wide and never counted twice, even under another filename or
series folder. Missing or invalid series metadata is also reported; validated,
deduplicated maps from those folders still contribute to global statistics,
rankings, and merits, and appear in report diagnostics. A missing or invalid
tournament root fails the import.

### Public tournament report flow

After installation, call the existing public Python API from a script or Python
session with access to the project packages:

```python
from application.tournament_report import generate_tournament_report
from models.lan_match import BestOf

output = generate_tournament_report(
    r"D:\LAN\tournament",
    r"D:\LAN\reports\tournament.html",
    best_of_by_series={
        "group-a": BestOf.BO1,
        "semifinal": BestOf.BO3,
        "final": BestOf.BO5,
    },
    tournament_id="lan-2026",
    title="LAN 2026 / Informe del torneo",
)
```

Open the returned `Path` locally in a browser. The generated HTML is standalone,
in Spanish, with embedded CSS; it requires no server or JavaScript. Original
source names and technical importer messages are preserved. Parent directories
are created, a non-HTML suffix is replaced with `.html`, and an existing
destination is overwritten. Keep reports outside the source series folders.

The report contains:

- an overview of the tournament and import counts;
- the global leaderboard and competitive MVP;
- merit titles with recipients and statistical evidence;
- statistics and rankings for accepted series and their maps;
- player details, including aliases, raw totals, derived statistics, and Impact
  components;
- data-quality diagnostics for invalid CSVs, skipped duplicates, and series
  metadata issues, including valid maps awaiting accepted series metadata.

Rankings are deterministic. The MVP is the first tournament-ranked player who
meets the existing participation eligibility rule; ineligible players remain on
the leaderboard. With no eligible player, MVP is unavailable. Merit titles are
independent awards: a player may receive several, and they do not change rankings
or Impact scores.

### Player Impact

v0.6 includes **Player Impact Rating v1.0**, a deterministic score in the range
0–100. It is our own transparent LAN metric, not HLTV Rating 2.0 or 3.0. It is
calculated from aggregated statistics at map, series, or tournament scope;
series and tournament Impact scores are not averages of map scores.
The full formula remains in [Player Impact Rating v1](docs/player_impact_rating_v1.md).

## Technical documentation

The detailed contracts remain the source for schemas, formulas, and edge cases:

- [LAN match CSV contract](docs/lan_match_csv_contract.md): required schema,
  validation, folder boundaries, BestOf metadata, deduplication, and diagnostics.
- [Player statistics contract](docs/player_statistics_contract.md): canonical
  identity, aliases, aggregation scopes, raw totals, and derived metrics.
- [Player Impact Rating v1](docs/player_impact_rating_v1.md): versioned formula,
  components, evidence, and tournament participation eligibility.
- [Player ranking contract](docs/player_ranking_contract.md): deterministic
  ordering, tie-breaks, and ranking eligibility data.
- [Player merit titles](docs/player_merit_titles.md): active catalog, recipient
  rules, tie-breaks, and evidence.
- [Tournament HTML report](docs/tournament_html_report.md): public APIs,
  presentation sections, partial imports, and standalone output behavior.

## Test architecture

The offline suite covers four layers:

- `tests/unit`: component contracts, scoring and objective behavior, structural
  invariants, moves, neighborhoods, optimizer behavior, and tournament domain
  contracts (statistics, Impact, rankings, and merit titles).
- `tests/integration`: tournament folder import, report generation, and the
  complete tournament analytics pipeline.
- `tests/acceptance`: synthetic 20-player FAST/STABLE/GLOBAL cross-component
  behavior and consistency with a fresh `ObjectiveEngine` evaluation.
- `tests/regression`: the reviewed LAN 2026 historical fixture, 20-player power
  fingerprint, deterministic initial generation, and deterministic STABLE
  behavioral fingerprint.

The [frozen tournament acceptance fixture](tests/fixtures/lan_tournament_acceptance/README.md)
is exercised by `tests/integration/test_lan_tournament_statistics.py`. It protects
the complete CSV-to-Spanish-HTML pipeline, including validation, deduplication,
aggregation, Impact, rankings/MVP, merit titles, canonical identity, and
diagnostics, against independently reviewed frozen expectations.

Run the full suite or coverage report with:

```powershell
python -m pytest
python -m pytest --cov --cov-report=term-missing
```

## Project architecture

```text
application/     balancing facade, statistics, Impact, rankings, merits, report flow
evaluation/      internal evaluation models and services
exporters/       balancing HTML and standalone Spanish tournament HTML/CSS
generators/      initial team generation
importers/       player import, LAN map CSV validation, tournament folder import
models/          player/team, map/series, statistics, Impact, ranking, report models
objective/       authoritative objective engine and restrictions
optimizer/       FAST, STABLE, and GLOBAL optimization
scoring/         individual player scoring
scrapers/        FACEIT data acquisition
tests/unit/      component-level tests
tests/integration/ tournament import/report flow and frozen tournament acceptance
tests/acceptance/ cross-component engine tests
tests/regression/ frozen LAN 2026 engine regression tests
docs/            detailed tournament analytics and reporting contracts
```

## Development workflow

The intended repository workflow is:

```text
Jira issue
  -> feature/SCRUM-XX-short-description
  -> development
  -> python -m pytest + ruff check .
  -> pull request
  -> GitHub Actions green
  -> squash merge to main
```

See `CONTRIBUTING.md` and `RELEASE_NOTES.md`.
