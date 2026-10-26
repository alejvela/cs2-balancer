# CS2 Balancer v0.8.0 — Engine Contract Hardening

v0.8.0 integrates the FAST/STABLE/GLOBAL engine contracts from SCRUM-46–52.
Python 3.11 or later is required.

- **SCRUM-46:** finite numeric validation and shared logical identity checks.
- **SCRUM-47:** exact transactional rollback, explicit local initial scores and
  complete search-work accounting.
- **SCRUM-48:** restart integrity, failure-safe STABLE publication and independently
  verified selected results.
- **SCRUM-49:** effective GLOBAL controls, removal of inert configuration and
  validated optional incumbents.
- **SCRUM-50:** audited mathematical bounds, safe fallback and explicit proof
  certificates separating exhaustion from certified optimality.
- **SCRUM-51:** precise budgets, counters, cooperative timing and consistent
  operational stop reasons/report metadata.
- **SCRUM-52:** cross-mode acceptance, adversarial evidence and executable migration
  guidance, preserving frozen production teams and scores.

## Upgrade from v0.7

Read the [migration guide](https://github.com/alejvela/cs2-balancer/blob/v0.8.0/docs/v07_to_v08_migration.md)
and [complete release notes](https://github.com/alejvela/cs2-balancer/blob/v0.8.0/RELEASE_NOTES.md).
Local results now require `initial_score`; stricter exceptions reject invalid
numeric/identity/transaction data. GLOBAL without an incumbent has nullable initial
score/improvement. Check the certificate before claiming optimality.

The five approved fingerprint differences are:

| Observation | v0.7 | v0.8 |
| --- | --- | --- |
| FAST evaluations | 737 | 1037 (SCRUM-47) |
| STABLE selected-local evaluations | 133 | 433 (SCRUM-47) |
| GLOBAL `base_seed` | 2026 | Removed (SCRUM-49) |
| GLOBAL `deterministic` | true | Removed (SCRUM-49) |
| GLOBAL `use_elo_bound` | false | Removed (SCRUM-49) |

The extra evaluations count searches without accepted moves. Removed keys were
inert; STABLE's own seed remains supported. Powers, teams, scores, component
weights/penalties and retained production defaults match the frozen comparison.
See the [machine-readable evidence](https://github.com/alejvela/cs2-balancer/blob/v0.8.0/docs/v08_fingerprint_evidence.json).

## Known limitations

GLOBAL without an incumbent is supported by the API, but its nullable improvement
currently causes `TypeError` in the existing HTML exporter. Use the default
incumbent-enabled HTML flow or consume the no-incumbent API result directly.

Time limits are cooperative and can overrun atomic work or final verification.
Incomplete search is not proof; no-incumbent interruption before a feasible
solution raises. Audited Power enclosures apply to documented CPython binary64
regimes; other cases use safe fallback. Exhaustive search may be expensive.
Offline tests do not verify live FACEIT service availability. APIs remain pre-1.0;
no new operator CLI, YAML workflow, HTML redesign or v0.9 features are included.

The wheel and source distribution identify version `0.8.0`. The source archive
includes migration documentation and test fixtures. Default `python main.py`
requires your roster/configuration and FACEIT credentials when live import is on.

[Full comparison with v0.7.0](https://github.com/alejvela/cs2-balancer/compare/v0.7.0...v0.8.0)
