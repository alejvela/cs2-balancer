# cs2-balancer v0.6.0

These notes describe v0.6.0 in preparation; they do not announce a public release.
Publication metadata belongs to SCRUM-36.

Version v0.5.0 established the engine-stabilization baseline. v0.6.0 formally
adds the complete **LAN Tournament Analytics & Reporting** pipeline implemented
under SCRUM-17. FAST, STABLE, and GLOBAL balancing remain available; this release
does not intend deliberate changes to balancing-engine behavior.

## Tournament ingestion and identity

Each CSV represents one played map under a strict map CSV contract. Each direct
child folder of the tournament represents a series, and only its immediate CSV
files are discovered. `matchid` does not define a series boundary. `BestOf` is
explicit metadata keyed by the series folder name, using the existing enum;
BO1/BO3/BO5 is never inferred by counting CSV files.

Discovery is deterministic and validation is strict. Structured diagnostics and
partial success preserve valid maps when other files are malformed or invalid.
Exact deduplication of parsed map data is tournament-global: a duplicate is
never counted twice, even under a different filename or series folder. Missing
or invalid series metadata is reported; validated, deduplicated maps remain
available for global statistics even when an accepted series cannot be built.
A missing or non-directory tournament root fails the import.

`steamid64` is the canonical player identity. Nicknames and team strings are
observed context and presentation data; nickname changes do not split a player
into different identities. Aggregation retains aliases and selects display names
deterministically.

See the [CSV and tournament import contract](docs/lan_match_csv_contract.md).

## Statistics and Player Impact Rating v1.0

Statistics are aggregated at map, series, and tournament scope. Derived metrics
are calculated from the corresponding aggregate totals. Identity, aliases, raw
totals, and derived metrics follow the
[statistics contract](docs/player_statistics_contract.md).

**Player Impact Rating v1.0** is our own transparent, deterministic metric in the
range 0–100, independent of ranking. It is not HLTV Rating 2.0 or Rating 3.0.
Its components are Combat, Opening/Entry, Multikill, Supported Clutch, Teamplay,
and Utility/Flash. Series and tournament scores are calculated from aggregated
statistics, never by averaging map Impact scores. The full versioned formula and
its limitations remain in the [Impact contract](docs/player_impact_rating_v1.md).

## Rankings, MVP, and merit titles

Map, series, and tournament rankings are deterministic, with stable tie-breaks.
Tournament participation eligibility is separate from the Impact Score: an
ineligible player remains on the leaderboard without a score or rank adjustment.
The report selects MVP as the first tournament-ranked player satisfying the
existing eligibility rule; if no player is eligible, MVP is unavailable.
See the [ranking contract](docs/player_ranking_contract.md).

v0.6 includes the deterministic SCRUM-25 merit-title catalog. Each awarded title
has exactly one recipient, deterministic tie-breaks, and statistical evidence.
One player may receive several titles; awards do not modify rankings or Impact.
The catalog and selection rules remain in the
[merit-title contract](docs/player_merit_titles.md).

## Tournament HTML report

The current Python API, `application.tournament_report.generate_tournament_report`,
composes the folder-to-report flow. It generates standalone Spanish HTML with
embedded CSS, no server, and no required JavaScript. Source names and original
technical importer messages are preserved for traceability.

The report includes an overview, global leaderboard, MVP, merit titles,
series/map statistics, and individual player details with Impact components and
statistical evidence. Data-quality diagnostics expose invalid files, skipped
duplicates, and series metadata issues, including valid maps awaiting accepted
series metadata. See the [report contract](docs/tournament_html_report.md) and
the [README usage example](README.md#public-tournament-report-flow).

## Frozen tournament acceptance fixture

SCRUM-24 introduces a frozen acceptance fixture protecting the complete pipeline:

```text
CSV → import → validation/deduplication → aggregation → Impact
    → rankings/MVP → merit titles → Spanish HTML
```

It also protects nickname changes with canonical `steamid64` identity, malformed
input, duplicates, BO1/BO3/BO5 metadata, and deterministic results across repeated
runs. Independently reviewed frozen expectations cover the statistical and
presentation contracts without regenerating expected outputs from production
results. The fixture is exercised by
`tests/integration/test_lan_tournament_statistics.py`; see its
[acceptance documentation](tests/fixtures/lan_tournament_acceptance/README.md).

## Compatibility and usage

Tournament analytics is additive to the v0.5 baseline; no complex migration is
required for the balancing engine. `pyproject.toml` remains authoritative for
version and dependencies. Balancing still runs from the repository root with:

```powershell
python main.py
```

FACEIT remains part of the balancing flow: the default live refresh requires
`FACEIT_API_KEY`. The tournament CSV-to-report flow does not require FACEIT and
is currently consumed through the Python API. To use it, organize map exports
in series folders, supply explicit `BestOf` metadata, and call the report API
shown in the README.

The project remains developer-oriented, without a mature CLI or a stable public
application architecture. These APIs do not carry a v1.0 stability promise.
BestOf and played-map counts do not establish a series winner or completion.
GLOBAL remains bounded search: normal resource limits can stop it before search
exhaustion, and a normal result alone does not establish mathematical optimality.

## Deferred to v0.7+

The following is known, deliberately deferred work outside the delivered v0.6
scope, not a reason to invalidate this release. The broad roadmap separates
Application Foundation (v0.7), Engine Contract Hardening (v0.8), and Operator
Experience & CLI (v0.9), toward a Stable CS2 LAN Toolkit (v1.0). This is not a
commitment to deliver all remaining debt in v0.7.

### Application architecture

- Centralized typed configuration and a composition root.
- A common FAST/STABLE/GLOBAL application API and common application result
  boundary.
- Move GLOBAL orchestration and result adaptation out of `main.py`, reducing
  its responsibilities.
- Remove or replace empty factories and obsolete abstractions.

### Engine hardening

Later engine work, not necessarily part of v0.7, includes:

- GLOBAL validation/configuration hardening, including making configurable
  flags effective or removing flags that do not control actual behavior.
- Proof/optimality semantics, incumbent validation, and bound/objective
  compatibility.
- A consistent NaN/Infinity/non-finite policy.
- `MoveEvaluator` transaction/rollback hardening.
- STABLE identity/result verification and optimizer result/history consistency.

### Operator experience

- A deliberate CLI and explicit configuration-file/CLI precedence.
- Explicit FACEIT refresh/offline modes.
- Operator-facing diagnostics.

---

# cs2-balancer v0.5.0

Version 0.5.0 is the engine-stabilization baseline for this internal,
developer-oriented application.

## Engine stabilization

- Established `ObjectiveEngine` as the authoritative team-quality score.
- Stabilized the production player scoring model.
- Enforced structural optimizer invariants and fresh final-score reevaluation.

## Optimization

- FAST local optimization from the generated composition.
- Deterministic STABLE multi-start optimization and reproducible selection.
- Advanced bounded GLOBAL search using a verified STABLE warm start.

## Testing

- 408-test v0.5.0 baseline at the start of the release-hygiene ticket.
- Unit coverage for scoring, objective restrictions, moves, neighborhoods, and
  FAST/STABLE/GLOBAL optimizer contracts.
- Synthetic 20-player acceptance coverage across all three optimization modes.
- Frozen LAN 2026 regression coverage, including the 20-player power fingerprint,
  deterministic initial generation, and deterministic STABLE behavior.

## GLOBAL limitations

GLOBAL is an advanced bounded mode externally orchestrated through `main.py`.
Normal limits can stop a run before search exhaustion, so a result does not imply
proof of mathematical optimality unless the solver explicitly establishes proof
under its admissibility and precondition assumptions. Additional GLOBAL contract
and configuration hardening is deferred.

## Known v0.6+ debt

- Centralized typed configuration and composition.
- A common FAST/STABLE/GLOBAL application API.
- GLOBAL validation and configuration hardening.
- Consistent non-finite numeric validation.
- Optimizer transaction and result hardening.
- Direct external-adapter and report coverage.
- A deliberate CLI and application architecture.
- Removal of stale configuration and unused legacy code.

## Install and run status

Python >= 3.11 is required, and `pyproject.toml` is authoritative. This remains a
developer application without a mature CLI. Default application execution
refreshes FACEIT data and requires `FACEIT_API_KEY`; the fully offline test suite
requires neither FACEIT access nor credentials.
