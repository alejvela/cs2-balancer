# v0.8 engine acceptance and release readiness

Authority: [SCRUM-52 comment 10778](https://alevelara.atlassian.net/browse/SCRUM-52?focusedCommentId=10778).
Base: `d05e329017c05fcf3bc2f2bf2bf34c3f265ebc96`.
Branch: `feature/SCRUM-52-v08-engine-acceptance-migration`.
Release remains subject to independent Tech Lead review; do not merge automatically.

## Acceptance matrix

| Evidence | FAST | STABLE | GLOBAL |
| --- | --- | --- | --- |
| Public application, production factories, fresh objective consistency | Pass | Pass | Pass |
| Exact instance/logical pool, team size, seed separation, components/penalty | Pass | Pass | Pass |
| Duplicate logical identity and bool/NaN/+inf/-inf objective weight rejection | Pass | Pass | Pass |
| Literal `python main.py`, offline CSV -> real application -> real HTML | Pass | Pass | Pass |
| Existing 20-player production fingerprint and v0.7 report compatibility | Pass | Pass | Pass |
| SearchWork / transactional restoration | Shared local suite | Shared local suite | STABLE warm start suite |
| Restart integrity, selected vs quality restart, last_run invalidation | N/A | Pass, reused suite | Warm start |
| No-incumbent nulls and independently certified exhausted run | N/A | N/A | Pass |
| Invalid incumbent, limits, safe pruning and incomplete proof | N/A | N/A | Pass, reused suites |

New executable evidence: `tests/acceptance/test_v08_engine_contracts.py` (26 cases)
and `test_v08_fingerprint_evidence.py` (one comparison). Subprocess tests inject
only typed bootstrap config through a temporary `sitecustomize.py`; production
`main.py`, importers, factories, optimization and HTML remain unchanged. They do
not claim live FACEIT connectivity. Existing `test_main_entrypoint.py` additionally
observes CSV/application/report metadata and object flow, PREASSIGNED routing and
exit codes (0 success, 1 handled failure, 130 cancellation).

## Adversarial evidence reused

All paths below are relative to `tests/`; the complete suite executes them.

| Boundary | Existing executable evidence |
| --- | --- |
| Numeric finite policy, mutable objective aggregates, overflow | `unit/test_foundation_numeric_contracts.py` |
| Shared logical identities, duplicate team instances/indexes | `unit/test_foundation_identity_contracts.py` |
| Partial apply, undo failure, rollback failure precedence, exact restoration | `unit/optimizer/test_transaction_contracts.py::test_temporary_transaction_failure_precedence`, `test_definitive_move_rollback_precedence`, `test_real_restoration_checks_exact_identity_and_order` |
| Corrupt factory/local restart; success then failure clears last_run | `unit/optimizer/stable/test_stable_optimizer.py::test_structure_and_pool_corruption_fails_before_selection`, `test_success_then_failure_clears_last_run` |
| Invalid incumbent/disabled incumbent and flags | `unit/optimizer/global_search/test_global_input_config_contracts.py`, `unit/test_global_execution.py` |
| Unknown/unsafe bounds, roots, symmetry and exact proof oracle | `unit/optimizer/global_search/test_global_bound_proof_contracts.py` (including every-switch reference optimum, outward enclosure against every descendant and unknown calculator tests) |
| One-unit/exact exhaustion, no proof after interruption, priority and fake clocks | `unit/optimizer/global_search/test_global_budget_result_contracts.py` |
| Report score/team/certificate parity and absent fields | `unit/test_global_report_result.py`, `unit/test_global_execution.py`, new no-incumbent acceptance |

This reuses focused fault injection and independent exhaustive oracles rather
than repeating every low-level adversarial case through every mode.

## Fingerprint reproduction

`v08_fingerprint_evidence.json` stores raw v0.7 and candidate observations,
provenance, unchanged categories, frozen fixture SHA-256 values (Git blob bytes)
and each approved difference. Production defaults are snapshotted in full;
execution uses existing deterministic acceptance budgets (three STABLE restarts,
500 GLOBAL nodes / 50 evaluations, no time limit) and 20 synthetic players.
Elapsed times are deliberately excluded. Score comparisons across Python versions
retain the existing absolute `1e-6` tolerance; identity/counters/config compare exactly.

To reproduce, extract `git archive v0.7.0` into a separate directory, then run:

```text
python tests/acceptance/v08_fingerprint_probe.py PATH_TO_V07 v07-observed.json
python tests/acceptance/v08_fingerprint_probe.py . v08-observed.json
pytest tests/acceptance/test_v08_fingerprint_evidence.py tests/regression
```

The probe imports from the explicitly selected checkout and writes observations
to the requested output, never to the baseline fixtures. Review differences before
editing evidence. The acceptance test also applies the five declared migrations
to the old snapshot and requires exact equality to the stored new snapshot, so
unlisted drift fails.

| Observation | v0.7 | v0.8 | Authority |
| --- | --- | --- | --- |
| FAST total evaluations | 737 | 1037 | SCRUM-47: 300 no-move evaluations now counted |
| STABLE selected local evaluations | 133 | 433 | SCRUM-47: 300 no-move evaluations now counted |
| GLOBAL `base_seed` | 2026 | absent | SCRUM-49: inert field removed |
| GLOBAL `deterministic` | true | absent | SCRUM-49: invariant capability, inert switch removed |
| GLOBAL `use_elo_bound` | false | absent | SCRUM-49: unimplemented switch removed |
| Powers, team membership, all scores/components/weights/penalties | frozen | unchanged | No tuning |
| GLOBAL DFS/prune counters and stop reason | frozen | unchanged | Budget-limited acceptance remains unproven |

Frozen LAN 2026 fixture and baseline blobs are unchanged from v0.7. That baseline
retains its original 0.5.0 provenance; it is not relabeled or regenerated.

## Release checklist and measured evidence

- [x] Authoritative brief and exact baseline verified.
- [x] Cross-mode application and script acceptance; executable migration example.
- [x] Frozen fixtures retained and individually justified comparison table.
- [x] [Migration guide](v07_to_v08_migration.md) covers APIs, config, exceptions,
  result metadata, compatibility and rollback.
- [x] Ruff: `python -m ruff check . --exclude .tmp --exclude .venv-1` passes locally
  (exclusions are untracked local archives/environment only; CI uses `ruff check .`).
- [ ] Final full pytest/coverage measurement and PR CI results: recorded in PR.
- [x] Existing `.github/workflows/tests.yml` runs Ruff + full pytest on Python
  3.11 and 3.12, and coverage on 3.12. Configuration inspection alone is not a
  green CI claim; actual job URLs/results are recorded in PR after push.
- [x] No production code, scoring/tuning, mathematical bounds, algorithms,
  CLI/YAML/HTML changes, version bump or v0.9 features.
- [ ] Independent Tech Lead review and release approval. No merge performed.

Initial local coverage exposed a test-harness issue: script subprocesses started
outside the repository did not discover the same coverage configuration, mixing
statement/branch data. The harness now starts in the repository with inputs and
outputs still isolated in temporary directories. The focused coverage run passes.
Final measurement uses an isolated `COVERAGE_FILE`. Generated logs/coverage stay
in ignored `output/`, not release fixtures.

## Remaining risks and limits

- Time limits are cooperative. Atomic objective/bound calls and final verification
  are not preempted; total elapsed may exceed the configured deadline.
- Bounded search may return an unproven incumbent; without any feasible incumbent
  it raises. Exhaustion alone, confidence and high score are not certificates.
- The audited Power enclosure targets CPython binary64 round-to-nearest on
  3.11/3.12/3.14 and the data/size regime in the bound audit. Other regimes and
  unknown objectives use conservative/exhaustive fallback, potentially much slower.
- Small deterministic fixtures and exhaustive tiny oracles do not establish
  practical exhaustive-search performance for production-sized events. No live
  FACEIT/network availability or hard real-time behavior is claimed.
- Player references and nested metadata remain caller-owned; do not mutate them
  concurrently with a run. Integrity failures require discarding the composition.
- External consumers must migrate removed config keys, explicit local initial score,
  new work totals and optional GLOBAL scores before release. No restart recovery,
  new operator CLI, analytics or v0.9 workflow is included.
