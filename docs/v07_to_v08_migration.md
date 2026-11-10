# v0.7 to v0.8 engine migration

SCRUM-52 accepts the integrated SCRUM-46 through SCRUM-51 contracts against
`main d05e329017c05fcf3bc2f2bf2bf34c3f265ebc96`. The comparison release is
v0.7.0, commit `2fb6a2c7248387538f89d2a040fa94601034e949` (the annotated tag
object is not the release commit). Package metadata now identifies the v0.8.0
release candidate; publication and tagging remain separate approval steps.

Python >=3.11 remains required. CI targets CPython 3.11/3.12. Local acceptance
also runs on CPython 3.14.6. Install with `python -m pip install -e ".[dev]"`.
The public route remains `BalancingApplication(config).run(BalancingRequest(...))`.
`python main.py` remains the developer bootstrap: typed production defaults,
CSV/FACEIT input, application, console and HTML. It does not load new command-line
flags or a new YAML schema. Default FACEIT import requires credentials; acceptance
uses offline CSVs and substitutes only bootstrap configuration in a subprocess.

## Migration matrix

| Surface | v0.7 behavior / caller assumption | v0.8 contract and required migration |
| --- | --- | --- |
| Decision numbers (46) | Invalid numbers could reach comparisons or clamps | `finite_real` rejects bool/non-Real with `TypeError`; NaN, infinities and float-conversion overflow with `ValueError`. Validate before invoking engine APIs. Never turn invalid values into zero. Finite range/clamp rules remain. This is an engine boundary policy, not a promise to redesign all importers. |
| Objective/restriction mutation (46) | Construction alone could appear sufficient | Mutable score/weight/penalty operands and aggregates are revalidated, including zero-weight paths and overflow before clamping. Catch errors at the run boundary. |
| Logical identity (46) | GLOBAL pool uniqueness could differ from STABLE | Shared `logical_player_identity`: explicit identity, Steam ID, nickname/nick, then stable structural fallback. Normalization/prefixes remain compatible. Remove duplicate identities even when objects or Steam IDs differ. Anonymous ordering no longer depends on memory addresses. |
| Structural identity (46/47) | Equal objects could mask corrupt restoration | Repeated mutable Team instances and repeated player indices are rejected. Equivalent fresh players may satisfy logical pool checks, but move rollback must restore the exact original instances and order. Distinct teams may share labels. |
| Temporary/definitive moves (47) | An exception could hide cleanup failures | Partial apply failures restore snapshots; undo is attempted only after completed apply. Failed restoration/validation raises `TransactionIntegrityError`, preserving `operation_error`, `undo_error` and cause. Successful restoration preserves the operational exception; undo-only failure raises `RuntimeError` with cause. Abort the run on integrity failure; do not continue with the damaged graph. |
| Local result construction (47) | Initial score inferred from history/final result | Supply keyword-only `initial_score` to `OptimizationResult` and `from_history`; omission raises `TypeError`. Improvement is final minus actual initial, including restored best-state results. Both public import paths still refer to the same class. |
| Local work/history (47) | Evaluation/time totals reflected accepted moves | Accepted iterations remain movements; immutable `search_work` also records completed searches without an accepted move. Totals and summaries include this work once; summaries add `searches`. STABLE evaluation budgets can consequently stop sooner. |
| STABLE restarts (48) | Restart corruption or previous `last_run` could be trusted | Every restart/local output must preserve logical pool, team count and size multiset. Corruption fails immediately. `last_run` is cleared before validation and published only on success; `require_last_run()` fails after errors. There is no recovery/retry policy. |
| STABLE selection (48) | Best restart conflated selection with quality improvement | Run `best_restart_index` describes selected result; `best_quality_restart_index` describes last real quality improvement. Legacy convergence snapshot best-index names retain quality meaning. Independent final evaluation verifies components/metadata and publishes the fresh objective result. Initial score/history still describe the selected local run. |
| GLOBAL config removal (49) | `use_elo_bound`, `deterministic`, `base_seed` accepted but inert | Remove all three constructor/serialized keys. No ignored aliases; passing them raises `TypeError`. STABLE's base seed remains. GLOBAL is deterministic by design with deterministic inputs/objective and non-time-limited execution. |
| GLOBAL controls (49/50) | Some switches were inert | Retained flags gate the respective lookahead/Power work. Hard capacity and seed assignment constraints always apply. Direct optimizer construction must wire `GlobalBoundCalculator(pruning_policy=config.pruning_policy)`; mismatches fail. |
| Incumbent enabled (49) | Caller-supplied score/teams trusted too broadly | Teams are required and checked for exact count/sizes/logical pool, unique identities/Team objects and protected seeds. Fresh logically equivalent players are allowed; protected status comes from problem metrics. Optional score must be finite and match independent evaluation within tolerance. Invalid structures/scores raise before search. |
| Incumbent disabled (49) | Disabling could still use STABLE | Set `use_incumbent=False` and omit both incumbent arguments. Application bypasses STABLE/generation/local search. Supplying either argument is an error. Initial score and improvement are `None`, JSON `null`; `incumbent_improved=False`. Interruption before any feasible solution raises `RuntimeError`, not an empty success result. |
| Bounds (50) | Calculator estimate/weights could imply safety | Actual objective/scoring compatibility is audited. Safe outward Power enclosure, proven whole-objective ceiling or exhaustive fallback is selected. Unknown objectives have no assumed 100 ceiling. Custom callbacks/roots cannot silently establish proof. See the mathematical audit linked below. |
| Proof (50) | Exhaustion could be treated as optimality | `search_exhausted` is separate from `optimality_proven`. Immutable `GlobalProofCertificate` requires complete root, safe symmetry/pruning, verified traversal, exact ranking, incumbent domain witness and exact final score. A limit never proves optimality. `require_proof=True` requires all budgets `None`, exact ranking and verification; incomplete exhausted certification uses `PROOF_NOT_COMPLETED`. |
| GLOBAL counters (51) | Equality to a budget could imply interruption | A limit requires refusal of pending work. Exactly finishing the final branch at the budget is exhaustion. Counters count admitted DFS nodes/evaluated leaves/explicit prunes only. Incumbent/witness/final/report evaluations are excluded from DFS evaluations. See equations below. |
| GLOBAL timing (51) | Elapsed could mean DFS alone | Optimizer time includes validation/preparation/incumbent/DFS/final verification/certification. Application GLOBAL time also includes metric/problem creation and report verification, excludes preceding STABLE and presentation. Deadlines share the start but are cooperative; final verification completes even after expiry. |
| GLOBAL report (51) | Tolerantly equal score could preserve proof | Report uses the exact GLOBAL Team instances and authoritative verified score. Tolerated nonexact score invalidates `final_score_exact` and proof; proof mode rejects it. Counters/reason/certificate/exhaustion delegate to validated result and metadata carries certificate/exhaustion. |
| Compatibility/deprecations (46) | Legacy enumeration helpers might be usable | Unimportable, unconsumed `MoveSource` removed. `Neighborhood.generate()` compatibility hook still returns `None`; supported enumeration is `iterate()`/`sample()`. DoubleSwap accessors remain. No new deprecation aliases or warnings. |

## Stop reasons, budgets and nullable fields

GLOBAL reasons are closed: `SEARCH_EXHAUSTED`, `NODE_LIMIT`, `EVALUATION_LIMIT`,
`TIME_LIMIT`, `PROOF_NOT_COMPLETED`. Exhaustion and incomplete proof have
`search_exhausted=True`, `stopped_by_limit=False`; limit reasons have the inverse
and `optimality_proven=False`. Exhaustion is necessary, not sufficient, for proof.
Unknown reasons, inconsistent flags/certificates, invalid counters or elapsed values
are rejected. Preserve operational reasons rather than replacing limits with a
generic proof failure.

Node admission checks nodes, evaluations, then time. An already admitted leaf
checks evaluations, then time; it does not charge another node. `None` disables
a budget; positive integer node/evaluation limits exclude bool, time must be finite
and positive. No checks occur on unwind or hard-rejected candidate branches.

```text
capacity_prunes + seed_prunes + bound_prunes == pruned_nodes
complete_solutions_evaluated + pruned_nodes <= nodes_visited
nodes_visited <= maximum_nodes                    # if configured
complete_solutions_evaluated <= maximum_evaluations # if configured
```

STABLE retains `perfect_score`, `target_confirmed`, `convergence`, `restart_limit`,
`evaluation_limit`, `elapsed_limit`; these are not GLOBAL reason strings.
FAST keeps local accepted history and SearchWork rather than a GLOBAL certificate.
Do not interpret STABLE confidence or a high score as a global proof.

Read `initial_score`/`improvement` as optional for no-incumbent GLOBAL. Preserve
`None` in stored results and show `N/A` where appropriate. Read optional metadata
with `.get()`: `stable_optimization` is absent when STABLE did not run;
`global_optimization` is present for GLOBAL and includes the certificate/exhaustion.
PREASSIGNED requests remain evaluation-only regardless of requested optimization
mode, with no optimization metadata. `optimization_deterministic` describes the
mode capability, not a timing guarantee. Ignore elapsed fields when comparing replays.

## Executable migration example

Run `python -m docs.v08_migration_example` from the checkout. The example below
uses the production factories with a small event and a bounded data domain; its
source is also executed in acceptance tests.

```python
from docs.v08_migration_example import run_example

report = run_example()
assert report.initial_score is None
assert report.improvement is None
assert report.search_exhausted
assert report.optimality_proven
assert report.proof_certificate.optimality_proven
```

For direct local-result construction, replace inferred initial scores with the
actual initial evaluation:

```python
result = OptimizationResult(
    teams=teams, objective_result=final_objective,
    history=history, initial_score=initial_objective.score,
)
```

For persisted GLOBAL config, explicitly remove `use_elo_bound`, `deterministic`
and `base_seed` before constructing `GlobalOptimizationConfig(**data)`. Review
each removed field; do not silently discard arbitrary unknown keys. Proof mode
requires all budgets disabled. For interactive use retain budgets and accept an
unproven best-so-far result.

## Fingerprints and rollback

[Machine-readable evidence](v08_fingerprint_evidence.json) contains both actual
snapshots and five individual authorized differences. FAST evaluations are
737 -> 1037 and STABLE 133 -> 433 (SCRUM-47); the three inert GLOBAL keys are
removed (SCRUM-49). Powers, memberships, initial/final scores, restriction weights,
scores/penalties, GLOBAL counters and retained defaults are unchanged. This is
deterministic fixture evidence, not a claim that arbitrary time-limited runs are
bitwise identical. Existing LAN fixture bytes are unchanged. See
[acceptance/readiness](v08_release_readiness.md) for reproduction and limitations.

Before upgrading, preserve your environment lock, input/config snapshot and v0.7
outputs. On failure discard the current composition and rerun from original input
after correcting invalid data. For rollback deploy v0.7.0 with its own compatible
config/result reader in a separate environment; do not feed new nullable results
or removed-key schemas blindly into old consumers. No database/schema migration
or automatic in-place downgrade is provided. Keep v0.8 evidence for diagnosis;
never overwrite frozen fixtures to mask drift.

## Detailed contracts

- [46: numeric/identity foundations](SCRUM-46-foundation-contracts.md)
- [47: transactions/local results](transaction_local_contracts.md)
- [48: STABLE restarts](stable_restart_contracts.md)
- [49: GLOBAL input/config](global_input_config_contracts.md)
- [50: bound mathematics/proof obligations](global_bound_proof_contracts.md)
- [51: budgets/counters/timing/results](global_budget_result_contracts.md)

Earlier per-ticket documents describe deferrals at their implementation time;
this consolidated matrix describes the completed SCRUM-46..51 integration.
