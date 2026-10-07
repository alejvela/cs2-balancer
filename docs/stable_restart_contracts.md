# STABLE restart and result contracts (SCRUM-48)

`optimize_with_details()` clears `last_run` before validation and only publishes a
complete, verified run. `optimize()` delegates to it. Any failure propagates with
its original context, leaves `last_run` as `None`, and makes `require_last_run()`
raise. Corrupt restarts are hard failures; no restart recovery is attempted.

An immutable initial invariant captures team count, the sorted tuple of team
sizes (a multiset), and `SolutionSignature`. The signature uses SCRUM-46 logical
player identity and rejects duplicate identities. Every factory output is checked
before local search and every local result before selection or tracking. Fresh
objects with the same logical identities are valid; team order is irrelevant.

`StableOptimizationRun.best_restart_index` follows the selected local result,
including secondary and canonical tie-breaks. `best_quality_restart_index`
explicitly exposes the convergence snapshot's last real quality improvement.
The snapshot's legacy `best_restart_index`/`best_restart_number` retain their
quality meaning for compatibility. Serialization includes the explicit quality
name at both levels. Tracker registration, patience, thresholds and records keep
their existing semantics. A canonical tie can therefore select restart 1 while
the last quality improvement remains restart 0.

Before publication, STABLE calls
`local_optimizer.evaluator.objective.evaluate(selected.teams)` using the same
engine instance as local search. Aggregate and restriction scores must be finite
and agree within `score_tolerance`; penalties and weights must agree exactly.
Restriction keys, names and details must also agree. Both claimed and verified
numeric values use `models.numeric.finite_real` (including mutable result fields).
The returned `OptimizationResult` is a new wrapper with the fresh authoritative
`objective_result`, preserving the selected local teams, `initial_score`, history
(including SearchWork), title and metadata. The extra verification is orchestration
work and does not fabricate local SearchWork or a cross-restart initial score.

`SolutionSelector` keeps its ordering and tolerance rules but rejects non-finite
and boolean numeric fields even before shortcuts or canonical tie-breaking.
Deterministic inputs/components retain selection and convergence reproducibility;
wall-clock fields are excluded from replay comparisons.

GLOBAL incumbent semantics, bounds/proofs, budgets/counters and failed-restart
recovery remain deferred to SCRUM-49+ or separately authorized work. No restart,
objective, scoring, configuration or reporting tuning is included.
