# GLOBAL budgets, counters and result semantics (SCRUM-51)

This contract extends SCRUM-49 inputs and SCRUM-50 proof certificates. It does
not change scores, weights, pruning mathematics, symmetry or branch ordering.

## Counters

All six counters are nonnegative Python integers; booleans are rejected.

- `nodes_visited`: states admitted into DFS after the entry budget check. Includes
  internal nodes, evaluated leaves, explicitly pruned nodes and an admitted leaf
  interrupted before its evaluation. A refused entry is not a visited node.
- `complete_solutions_evaluated`: complete-state objective evaluations inside DFS.
  Incumbent evaluation, canonical incumbent witness evaluation, independent final
  verification and application report verification are excluded.
- `pruned_nodes`: admitted nodes discarded by an explicit bound decision.
- `capacity_prunes`, `seed_prunes`, `bound_prunes`: mutually exclusive decisions
  `capacity_impossible`, `seed_impossible`, `upper_bound`, respectively.

The result validates:

```text
capacity_prunes + seed_prunes + bound_prunes == pruned_nodes
complete_solutions_evaluated + pruned_nodes <= nodes_visited
0 <= nodes_visited <= maximum_nodes                 (when configured)
0 <= complete_solutions_evaluated <= maximum_evaluations (when configured)
```

The first two equations are structural result invariants; the last two are
enforced by the solver against its configuration. Hard-constraint candidate
rejections before child creation and symmetry omissions are not visited/pruned
nodes. No fictitious nodes or evaluations are charged for them. Results do not
carry budgets, so their constructors cannot independently validate budget bounds.

## Budget boundaries and priority

Before admitting a DFS node, check **nodes, evaluations, then time**, in that
order. The evaluation budget is a search-wide admission stop after that many
complete DFS evaluations, even if the next pending node might be prunable.
Before evaluating an already admitted complete node, check **evaluations, then
time**; its node has already been charged, so checking the node budget again
would incorrectly refuse the last permitted leaf. Counters increase only for
operations actually performed.

Do not check budgets on unwind or on hard-rejected candidate branches. Exactly
using the last permitted unit on the last branch is exhaustion. A limit means
an actual pending operation was refused, never merely that a counter equals a
threshold. Once stopped, the first reason is sticky. A real interruption never
proves optimality.

`None` disables a budget. SCRUM-49/50 validation remains: node/evaluation limits
are positive integers, time is finite and positive, and public `require_proof`
configurations require all budgets to be `None`. Defensive runtime interruption
tests additionally establish that proof mode cannot overwrite a real limit.

## Closed stop reasons

| Reason | Meaning | search_exhausted | stopped_by_limit | optimality_proven |
| --- | --- | --- | --- | --- |
| `SEARCH_EXHAUSTED` | No pending branch remains | true | false | Only with valid certificate |
| `NODE_LIMIT` | Pending node entry refused | false | true | false |
| `EVALUATION_LIMIT` | Pending entry/evaluation refused | false | true | false |
| `TIME_LIMIT` | Pending entry/evaluation refused at deadline | false | true | false |
| `PROOF_NOT_COMPLETED` | Exhausted in proof mode, certification incomplete | true | false | false |

The operational reason, exhaustion, interruption and certificate validity are
distinct facts. Unknown reasons, inconsistent flags, certificate/exhaustion
disagreement, invalid counters and nonfinite or negative elapsed times are
rejected. A certificate is still mandatory for any optimality claim. Exhaustion
alone is not a proof. `PROOF_NOT_COMPLETED` never replaces a limit.

## Timing

`GlobalOptimizer.optimize` starts its monotonic clock before validation. Its
`elapsed_seconds` ends after independent final evaluation and certificate
preparation. It includes validation, preparation/compatibility assessment,
incumbent and witness evaluation, DFS, verification and certification.

The search deadline uses this same start. Preparation/incumbent work therefore
consumes available search time; expiration is observed at the next DFS boundary.
Time is cooperative, not a hard wall-clock cap: objective calls, bound decisions
and other atomic operations are not preempted. Final verification and certificate
preparation always finish and are included in total time, but are not subject to
the search deadline. Expiration during the final atomic search operation with no
pending work, or during final verification, does not retroactively interrupt an
exhausted search. Total elapsed time can exceed the configured search deadline.

`run_global_optimization` measures the enclosing GLOBAL operation, including
metric/problem preparation, optimizer construction and the additional report
objective verification/certificate reconciliation. It replaces the result's
elapsed time with this enclosing duration, shared by the returned result and
report. This excludes the preceding STABLE warm start and subsequent report
formatting, CLI/HTML export. Tests use controllable clocks, never `sleep()`.

## Reporting and score verification

Reports require the exact GLOBAL Team instances, initial incumbent score and
final score. Public counters, timing, reasons and certificate delegate to the
validated result. Metadata includes exhaustion and the certificate as well.
The application preserves the existing consistency tolerance, but reconciles
the returned score and metadata with the independent authoritative evaluation.
Any tolerated nonexact score invalidates `final_score_exact` and optimality;
proof mode rejects it. This cannot upgrade a previously invalid certificate.

Absent incumbents remain `None` for initial score and improvement. If interrupted
before any feasible solution exists without an incumbent, the solver retains
SCRUM-49's explicit failure rather than fabricating a result.

## Verification and remaining work

Adversarial tests cover one-unit and exact budgets, simultaneous limits, clock
expiration across phases, defensive proof interruption, uncertified exhaustion,
invalid result fields, report parity, deterministic replay and an independent
exhaustive labeled-assignment oracle. Existing SCRUM-46 through SCRUM-50 tests
and production fingerprints remain unchanged.

Remaining [SCRUM-52](https://alevelara.atlassian.net/browse/SCRUM-52) work:
cross-mode FAST/STABLE/GLOBAL v0.8 acceptance, consolidated adversarial contract
coverage, revalidation of production configuration and supported entrypoints,
and migration/release documentation of every intentional change from v0.7.
For this change, that migration documentation must cover stricter result/report
validation, corrected exact-budget behavior, retained operational stop reasons,
expanded elapsed-time scope, reconciled report scores and the added exhaustion/
certificate metadata. No production fingerprint changes are intended. Deferred
v0.9 work remains deferred; this change does not promise preemptive wall-clock
termination or add phase-duration/auxiliary-evaluation telemetry.
