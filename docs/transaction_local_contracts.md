# Transactional local optimization (SCRUM-47)

Temporary evaluation snapshots player instances before `apply()`. Cleanup
attempts `undo()` only after a completed apply, then restores the snapshot
exactly once, including when apply partially mutates and raises. Restoration
checks the original instance at every position, not player equality.

| Failure | Raised outcome |
| --- | --- |
| Restoration or exact restoration validation | `TransactionIntegrityError`, with restoration failure as `__cause__`; `operation_error` and `undo_error` retain earlier exception objects and notes describe them |
| Operation and undo, restoration succeeds | Original operational exception, preserving its cause/traceback; `undo_error` and an exception note retain the undo failure |
| Undo only, restoration succeeds | Explicit `RuntimeError` caused by undo failure; message confirms restored state |
| Operation only, restoration succeeds | Original operational exception |

Definitive LocalOptimizer apply/structure/evaluation failures roll back from a
pre-apply snapshot. A failed rollback or rollback validation has the same
integrity precedence and preserves the operational exception. Successful
rollback checks exact instance/order and the original team sizes/player pool.
Best-state restoration, independent final evaluation, initial fallback and
the `SCORE_TOLERANCE` floor remain in force. Non-finite authoritative scores
fail through `models.numeric.finite_real` before comparison.

## Search work and accepted movements

`OptimizationHistory.iterations`, `count`, best/worst iteration and improvement
analytics still describe accepted movements. History now also holds immutable
`SearchWork` records containing phase, strategy, neighborhood, evaluations and
elapsed seconds. Each completed search in a returned local run contributes
exactly one record:

- `add(iteration)` records an accepted movement and its work together. Existing
  history construction from accepted iterations and `extend()` retain this behavior.
- `add_no_move(...)` records only work and rejects results containing a move.

These disjoint paths avoid counting accepted work twice. `clear()` clears both
collections. Totals use work records; phase/strategy/neighborhood summaries
include zero-accepted groups and a `searches` count. `as_dict()` preserves the
accepted `iterations` array and adds `search_work`. Scores in history remain
accepted-path analytics and may differ from the restored final solution.

`SearchResult` and `SearchWork` use the shared finite numeric policy. Evaluation
counts must be non-negative integers, and elapsed seconds must be non-negative.

## Result constructor migration

Both import paths for `OptimizationResult` refer to the same class. Its
constructor and `from_history()` now require keyword-only `initial_score`:

```python
result = OptimizationResult(
    teams=teams,
    objective_result=final_evaluation.objective_result,
    history=history,
    initial_score=initial_evaluation.score,
)
```

Omitting the initial score raises `TypeError`, including for non-empty history.
No first-accepted or final-score inference remains. Other positional arguments
and result properties stay compatible. LocalOptimizer supplies its actual
initial evaluation; the application decorator carries it through unchanged.
`improvement` is final score minus that explicit initial score even after best
snapshot restoration. An empty accepted history can therefore truthfully report
initial 72, final 72, accepted 0 and evaluations 100.

## Deferred scope

STABLE continues to return the selected local result: its initial score and
history describe that local run, not a new cross-restart result contract.
Correct local search totals also feed existing STABLE budget consumers, so
budget-limited runs can reach their existing limits sooner. Restart/last-run/
best-restart semantics belong to SCRUM-48. GLOBAL incumbent/flags (SCRUM-49),
bounds/proof (SCRUM-50), and budgets/counters (SCRUM-51) remain unchanged.
