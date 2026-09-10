# Application Foundation: behavior contract

SCRUM-37 freezes the published v0.6.0 baseline at
`c93ae772837d4a4c20173a516fd2f3a78e7ad71b` before SCRUM-38..42.
This is characterization, not the implementation of the v0.7 architecture.

## Current boundary and intended direction

In v0.6, `main.py` owns configuration constants, scoring construction,
objective construction, pipeline construction, application composition,
STABLE/GLOBAL configuration, GLOBAL orchestration, and GLOBAL report adaptation.
`LanBalancer` handles FAST and STABLE; selecting GLOBAL constructs a STABLE
balancer for the warm start. `main.run_global_optimization` then runs GLOBAL,
checks its score against a fresh objective evaluation, and adapts the result.
PREASSIGNED remains evaluation-only.

The intended v0.7 dependency flow is:

```text
typed configuration
        ↓
composition root / factories
        ↓
BalancingApplication
        ↓
FAST / STABLE / GLOBAL
        ↓
common application result
```

`main.py` will become bootstrap. These are responsibility boundaries, not final
API names, signatures, or a proposed implementation in this ticket. Application
code may depend on the engine; the engine must not depend on `main.py`, CLI,
presentation concerns, or filesystem bootstrap details. Tests may import the
current composition from `main.py`; that is not an engine dependency.

v0.7 is a **behavior-preserving refactor**. Deliberate engine semantic changes
belong to v0.8; operator experience and CLI belong to v0.9. Move the test setup
to the new composition boundary when it exists, preserving the expectations.
Do not regenerate baselines merely to make a refactor pass.

## Production composition protected here

`tests/acceptance/test_application_composition_contract.py` checks the actual
objects built by `main.py`, including defaults inherited from their constructors:

- Scoring: ELO/KD/ADR/KPR/Winrate/HS weights 40/25/15/10/7/3; logistic
  `(midpoint, steepness)` values `(1800, -0.003)`, `(1, -8)`, `(75, -0.10)`,
  `(0.70, -12)`, `(50, -0.12)`, `(45, -0.08)`; zero component fallback,
  minimum available weight 40, default power 0, and ActivityFactorModel defaults.
- Objective: Power/ELO balance/ELO spread/KD/size/seed weights 55/10/5/20/9/1;
  ELO logistic `(120, 0.025)`; spread thresholds 100/150/200/300/400;
  KD deviation 0.35; size 5 with penalty 25; seed level 1, maximum one per
  team, penalty 100 per excess player capped at 100.
- Pipeline: Quick Swap Improvement uses SwapNeighborhood/FirstImprovement,
  minimum improvement 0.01, 100 iterations; Final Swap Polish uses
  SwapNeighborhood/Exhaustive, minimum improvement 0.01, 30 iterations.
  Both are enabled and stop when no move is found.
- STABLE: target/perfect score 100; 30–150 restarts, patience 30, tolerance
  1e-6, seed 2026, 10 confirmation restarts, 20 unique solutions, no evaluation
  or time cap, and no perfect-score stop. Restart construction preserves seed
  separation, 1–6 swaps and redistribution ratio 0.50.
- GLOBAL: 500,000 nodes, 100,000 evaluations, 60 seconds; tolerance and minimum
  improvement 1e-6; incumbent, symmetry, seed/capacity pruning and power-bound
  flags true; ELO-bound false; deterministic true, require-proof false, seed 2026.
  Bound weights and the shared objective are also checked. Narrow private-field
  assertions are used only where these constructor settings lack public accessors.
- Application: four teams of five, strict CSV importer, snake draft and
  preassigned configuration, HTML exporter, and GLOBAL-to-STABLE warm-start routing.

## Coverage audit and reuse

| Existing protection | Contract reused without duplicating it |
| --- | --- |
| `tests/acceptance/test_engine_acceptance.py` | Synthetic 20-player fixture, canonical membership and invariant helpers; all-mode identity, capacity, seed and fresh-score checks; STABLE replay; bounded GLOBAL incumbent behavior |
| `tests/regression/test_lan_2026_regression.py` | Frozen real LAN power fingerprint, initial teams, STABLE teams and objective breakdown, deterministic replay |
| `tests/unit/scoring/` | Missing-data weighting, attribute normalization and activity behavior |
| `tests/unit/optimizer/stable/` | Selection, signatures, convergence and restart semantics |
| `tests/unit/optimizer/global_search/` | Limits and their priority, incumbent verification, strict improvement threshold, counters, final verification, exhaustion/proof flag, deterministic replay, bounds and small brute-force optimum |
| `tests/integration/test_lan_tournament_statistics.py` and `test_tournament_report.py` | Frozen tournament end-to-end fixture and public report flow; unchanged by this work |

`test_application_behavior_contract.py` adds the missing application-level
protection using the existing synthetic players and real production factories:

- FAST and STABLE: compact canonical team membership, initial/final score,
  objective components, report semantics and metadata. STABLE replays with fresh
  players. Three-restart STABLE uses the existing acceptance configuration.
- GLOBAL: actual warm start, problem construction, optimizer and report adapter;
  a one-node run retains the incumbent, while a 500-node/50-evaluation run improves
  it and stops at the evaluation limit. The adapter preserves caller and STABLE
  metadata, reports zero local moves/history and maps search counters. A focused
  test isolates the application's extra inconsistent-score rejection.
- Inactive GLOBAL switches are varied independently to characterize their
  current lack of effect on this bounded scenario, not to endorse that behavior.

Expected memberships and scores were observed on the unchanged baseline and
reviewed alongside fresh objective and structural checks. They are small test
constants, not generated snapshots. Production settings are checked separately;
the reduced-budget output tests do not claim to reproduce a full 60-second run.

## Quirks and deliberate exclusions

GLOBAL currently consumes a supplied incumbent even with `use_incumbent=False`.
The seed/capacity/power/ELO switches do not gate the bound calculator in the
current orchestration; `deterministic` and `base_seed` do not control traversal.
Symmetry breaking does affect traversal and is not included among inactive flags.
The report's deterministic metadata comes from OptimizationMode, so it remains
true even when the GLOBAL configuration says false. FAST advertises false.
These behaviors are frozen, not fixed.

Existing engine tests preserve the current exhaustion-based optimality flag;
this is not a new mathematical proof guarantee. Counter semantics exclude
incumbent and final verification from complete-solution evaluations. The
application tests preserve their mapping rather than snapshotting exact traversal
counts. ELO/KD bounds remain optimistic; no bound or validation hardening is added.

No exact elapsed times, timestamps, throughput, incidental player/team ordering,
or full-budget wall-clock-dependent solution is frozen. Canonical membership
ignores presentation order. Existing STABLE result/history consistency debt is
not repaired, and no requirement that STABLE outperform FAST is introduced.
No console/HTML byte snapshot or live FACEIT call is needed for these engine
composition contracts. Tournament fixtures, product code, CLI, configuration
formats and definitive future APIs are outside this ticket.
