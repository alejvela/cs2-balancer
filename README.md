# CS2 Team Balancer

CS2 team balancing engine for LAN events.

The project currently supports three optimization levels:

- **FAST**: local optimization from the generated composition.
- **STABLE**: deterministic multi-start local optimization.
- **GLOBAL**: branch-and-bound search able to prove optimality when the search space is exhausted.

## Current version

`0.5.0` — engine stabilization baseline.

The current development focus is:

1. objective-engine tests;
2. scoring tests;
3. optimizer tests;
4. acceptance tests;
5. CI and release hardening.

## Requirements

- Python 3.11+
- FACEIT API key when live FACEIT import is enabled.

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project with development dependencies:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## FACEIT API key

The application currently reads the API key from the environment variable:

```powershell
$env:FACEIT_API_KEY="your_key_here"
```

Do not commit API keys or `.env` files.

## Player input

The default source file is:

```text
data/players.csv
```

Expected columns:

```text
Nick,FaceitNickname,Seed,Team
```

`Team` may be left empty for automatic optimization.

## Run

```bash
python main.py
```

## Tests

Run the complete suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov --cov-report=term-missing
```

## Lint

```bash
ruff check .
```

Auto-fix safe Ruff findings:

```bash
ruff check . --fix
```

## Project architecture

Main layers:

```text
application/     application façade and report-facing results
evaluation/      internal evaluation models/services
exporters/       HTML reporting
generators/      initial team generation
importers/       player/stat import
models/          domain models
objective/       objective engine and restrictions
optimizer/       FAST, STABLE and GLOBAL optimization
scoring/         individual player scoring
scrapers/        FACEIT data acquisition
tests/           unit, integration and acceptance tests
```

## Development workflow

The intended repository workflow is:

```text
Jira issue
  -> feature/LAN-123-short-description
  -> development
  -> pytest + ruff
  -> pull request
  -> GitHub Actions green
  -> squash merge to main
```

See `CONTRIBUTING.md`.
