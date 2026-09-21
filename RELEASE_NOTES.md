# cs2-balancer v0.7.0 — Application Foundation

**Release candidate — not published.** Project metadata identifies this candidate
as `0.7.0`; `pyproject.toml` remains the sole package-version source of truth.
The candidate head commit is the review target. After approval and merge,
SCRUM-44 will tag and publish the SCRUM-45 merge commit. No tag or GitHub Release
is created during candidate preparation.

## Developer-facing changes

v0.7 changes where composition and orchestration live, not how teams are scored
or selected. Production weights, normalizers, activity, pipeline phases, restart
settings, GLOBAL budgets, seeds and tolerances retain their characterized behavior.
Tournament Analytics was delivered in v0.6 and is preserved, not a new v0.7 feature.

- **Typed configuration:** `ApplicationConfig.production_defaults()` centralizes
  event settings, paths, FACEIT, scoring, objective, pipeline, restart, STABLE,
  GLOBAL and debug/operator settings. Customize immutable Python values with
  `dataclasses.replace`; no CLI or YAML configuration loader is introduced.
- **Explicit composition:** real scoring, objective, pipeline, optimizer and GLOBAL
  factories build collaborators from typed inputs. The composition root creates
  a fresh execution graph for each application run.
- **Programmatic API:** `BalancingApplication.run(BalancingRequest(...))` returns
  `BaseReportResult`. Callers supply a `Sequence[Player]`, a team count and an
  `OptimizationMode`, with optional title and metadata. CSV paths and FACEIT I/O
  stay outside this API.
- **Execution modes:** FAST, STABLE and GLOBAL share that request/result boundary.
  PREASSIGNED evaluation is detected from player assignments by the application
  flow and bypasses optimization, including when GLOBAL is requested.
- **Application-owned GLOBAL:** STABLE warm start → GLOBAL search → final score
  verification → `GlobalReportResult`. Orchestration, verification and report
  adaptation belong to application, not `main.py`.
- **Common results:** `BaseReportResult` is the consumer boundary; existing
  `OptimizationResult`, `EvaluationResult` and `GlobalReportResult` retain their
  concrete semantics. No replacement result type or raw-search API is introduced.
- **Thin entrypoint:** `python main.py` remains supported for developers/operators.
  It handles bootstrap, optional FACEIT refresh, CSV import, request construction,
  one application call, validation, console output, HTML export and error handling.
  The mode banner now uses the returned report and appears after execution.
- **Reporting:** the reporting factory builds configured presentation scoring and
  `HtmlExporterV2` independently of execution composition. Bootstrap no longer
  retains internal composition through a callback or builds another engine for
  export. Offline acceptance verifies equivalent HTML and console presentation.

## Migration from temporary entrypoint helpers

The migration seams in `main.py` were not a stable public API. Code that imported
any of these removed helpers must migrate:

- `create_scoring_model`, `create_objective_engine`, `create_pipeline`, `create_balancer`;
- `create_global_metrics`, `create_global_problem`, `create_global_optimizer`,
  `run_global_optimization`.

Import-time configuration aliases and `_composition_config` have also been
removed. Setting old globals such as `OPTIMIZATION_MODE`, `RUN_FACEIT_IMPORT` or
`NUMBER_OF_TEAMS` no longer configures execution. Build an `ApplicationConfig`
and a `BalancingRequest`, then call `BalancingApplication` and consume its
`BaseReportResult`. Advanced composition callers can use the explicit factories
in `configuration/`; they do not need to import `main`.

For manual execution, continue using `python main.py` and customize the local
config construction with `dataclasses.replace`, as shown in the
[README](README.md#balancing-application-execution). FACEIT refresh remains enabled
by default and retains `FACEIT_API_KEY` semantics. Disabling it reuses the generated
CSV. No credentials or live FACEIT calls are required by the offline test suite.

See the [architecture](docs/application_architecture.md),
[application API](docs/balancing_application_api.md),
[typed configuration](docs/typed_application_configuration.md) and
[composition](docs/composition_root.md) contracts for signatures and ownership.

## Validation and deliberately deferred work

Candidate validation covers characterized scores/memberships, production
composition, the public API, GLOBAL retention/improvement and score rejection,
all four execution flows, real HTML export and offline CSV-to-report bootstrap.
Frozen LAN and tournament regression fixtures remain unchanged.

This release does not fix GLOBAL algorithms or establish stronger proof guarantees.
Engine Contract Hardening remains v0.8 work: ignored `use_incumbent`/pruning flags,
inactive deterministic/base-seed settings, incumbent validation, bound admissibility,
proof semantics, timing/budget semantics, Player identity, MoveEvaluator transaction
safety, STABLE restart/result semantics and non-finite policy. Operator Experience
& CLI remains v0.9; Stable CS2 LAN Toolkit remains the v1.0 direction.

The historical notes below are preserved as records of their respective releases,
including the preparation status and deferred work recorded at that time.

---

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
