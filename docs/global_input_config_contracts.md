# GLOBAL input and configuration contracts (SCRUM-49)

## Configuration migration (intentional v0.8 breaking change)

Remove `use_elo_bound`, `deterministic` and `base_seed` from GLOBAL configuration
construction. They are absent from constructor, presets, fields and serialization;
there are no ignored aliases. No ELO bound or RNG is introduced. ELO/KD remain
optimistic at 100. GLOBAL traversal is deterministic by design for the same
problem, retained configuration and deterministic objective. Mode-derived
`optimization_deterministic=True` describes this capability, not a config switch.
STABLE's own base seed and deterministic restart contract are unchanged.

## Incumbent API and result

With `use_incumbent=True`, `optimize(problem, incumbent_teams, incumbent_score=None)`
requires teams. Validation precedes objective evaluation: exact team count, Team
instances, no repeated Team object, exact sizes, no duplicate logical player
identity, exact logical pool, and the problem's protected-seed hard maximum.
Team IDs/order are irrelevant. Fresh Player objects with equivalent logical
identities are accepted. Protected status is resolved from the problem metrics by
shared SCRUM-46 logical identity, so fresh objects cannot hide protected players.
A supplied score must pass `models.numeric.finite_real` and agree with the
ObjectiveEngine score within tolerance. The verified incumbent becomes initial best.

With `use_incumbent=False`, call `optimize(problem)` with both incumbent arguments
absent/None. Supplying either is an explicit error. Best score/teams start as None;
no numeric sentinel or synthetic baseline is used. Before a first complete valid
solution, only enabled feasibility lookaheads can prune; score-bound pruning is
inactive. The first complete solution installs best regardless of minimum improvement.
The application skips STABLE/generation/local search in this mode and calls GLOBAL
without warm-start data. PREASSIGNED routing and enabled-incumbent behavior remain.

`GlobalOptimizationResult.initial_incumbent_score` is optional. With an initial
incumbent, improvement is final minus initial; without one, improvement is None and
`incumbent_improved` is False. GlobalReportResult initial score/improvement and
metadata preserve None, serialized as JSON null. Presentation of absent scores uses
N/A rather than inventing a STABLE baseline. Layout and enabled-incumbent output are
preserved. A run stopped before finding any solution cannot construct a valid result
and raises; budget/stop redesign is deferred.

## Retained controls and wiring

`GlobalOptimizationConfig.pruning_policy` derives an immutable `GlobalPruningPolicy`
from capacity/seed/Power flags. `configuration.global_factory` passes that policy to
GlobalBoundCalculator. The calculator is the sole owner of lookahead/bound gating;
GlobalOptimizer rejects mismatched policy/config wiring. Direct optimizer callers
must supply `GlobalBoundCalculator(pruning_policy=config.pruning_policy)`.

- `use_symmetry_breaking`: optimizer chooses canonical available team indices when
  true, all capacity-available indices when false. Branch ordering is unchanged.
- `use_capacity_pruning`: gates only the capacity-impossible lookahead. False never
  calls that lookahead or produces its prune events. Physical assignment capacity
  and exact final team sizes remain hard constraints.
- `use_seed_pruning`: gates only the seed-impossible lookahead. False never calls
  it or produces seed-lookahead prune events. Root/incumbent/assignment seed maxima
  remain hard constraints. Root protected counts must match authoritative metrics,
  preventing an undercount from bypassing later assignments.
- `use_power_bound`: gates Power interval/bound work in bound evaluation. False
  uses a fully optimistic 100 contribution and empty Power diagnostics. Without
  an incumbent, Power work is also unnecessary and skipped. Existing Power math,
  weights and combination rules are unchanged.

Scores present at optimizer/result/bound/application verification boundaries use
`finite_real`, rejecting bool, NaN and infinities. None represents absence only.

Replay tests disable time limits and compare canonical teams/signature, score,
nodes, evaluations and all prune counters, excluding elapsed time. Capacity
lookahead cannot naturally fail for physically valid exact-capacity states;
its counter test injects a false decision at a valid root, without permitting
an invalid problem or changing physical capacity.

## Deferred debt

Objective/bound admissibility and proof semantics belong to SCRUM-50. Node,
evaluation, time budgets/counters and stop semantics belong to SCRUM-51. No new
ELO bound, randomness, scoring tuning, CLI/YAML configuration, HTML layout redesign,
analytics or importer changes are included. Frozen production defaults retain
incumbent=True and all implemented pruning features enabled.
