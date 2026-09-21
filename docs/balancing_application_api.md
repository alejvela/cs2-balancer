# Public balancing application API (SCRUM-40/41)

See [application architecture](application_architecture.md) for the consolidated
architecture and SCRUM-43 acceptance matrix. This document details the API;
the baseline below records the original SCRUM-41 step.

SCRUM-41 baseline: `9df99f1229262047d863e32bab7d31bdc201d28c` (SCRUM-40).

```python
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from configuration.application_config import ApplicationConfig
from optimizer.modes.optimization_mode import OptimizationMode

config = ApplicationConfig.production_defaults()
application = BalancingApplication(config=config)

# players is a Sequence[Player] supplied by the caller.
result = application.run(
    BalancingRequest(
        players=players,
        number_of_teams=4,
        optimization_mode=OptimizationMode.FAST,
        title="LAN report",
        metadata={"event": "LAN CS2"},
    )
)
print(result.final_score, result.metadata)
```

`BaseReportResult` is the common public result contract. It already owns teams,
objective, scores, penalties, restrictions, metadata, execution/history properties,
serialization and summary. The API returns the existing concrete report result
unchanged; it does not introduce a duplicate `BalancingResult`, recalculate scores
or rename metadata. FAST/STABLE use native application execution through
`LanBalancer.run_players()`.

`BalancingRequest` is frozen/slotted execution data: players, number of teams,
`OptimizationMode`, optional title and metadata. It contains no scoring or search
configuration and no file source. The player collection is copied to a tuple and
metadata to a read-only top-level mapping. Player identity is preserved; nested
metadata values are not deep-copied. Each run receives a new metadata dict, so
engine decoration and later top-level changes to result metadata do not affect
the request or the caller's original mapping.

Request validation rejects None/empty players, nonpositive or noninteger team
counts, non-enum modes, non-string titles and non-mapping metadata. Blank titles
retain the existing result handling. Player validity, identity, assignments and
other engine invariants remain the responsibility of existing collaborators.

The application keeps immutable `ApplicationConfig` and uses
`create_balancing_composition()` once per run with a replaced optimization mode
and event team count. Request team count governs execution and the derived
expected player count; team size and all tuning remain config inputs. Each call
gets fresh scoring, objective, generators and optimizers. FAST → STABLE → GLOBAL → FAST
on one service does not mutate a shared balancer mode or retain optimizer state.
The optional `composition_factory` callable must preserve this fresh-graph
contract. Tests and the entrypoint can use it to observe the exact run graph.

PREASSIGNED continues to be detected from `player.team_number`. It returns the
existing evaluation result, preserves teams and bypasses optimization regardless
of requested optimization mode. GLOBAL therefore needs no runner for PREASSIGNED.

## Production GLOBAL execution

`BalancingApplication(config)` now executes FAST, STABLE and GLOBAL without
runner injection. Select `OptimizationMode.GLOBAL` in the same request shown
above. The default `ApplicationGlobalRunner` lives in
`application/global_execution.py`; it has no dependency on `main`.

The flow is unchanged: the per-run composition configures `LanBalancer` as
STABLE, the application obtains its warm start, and the GLOBAL runner adapts
players to `GlobalPlayerMetrics`. It uses `global_factory.create_global_problem`
and `create_global_optimizer`, passing exactly `warm_start.teams` and
`warm_start.final_score` as incumbent. It then evaluates the search teams with
that composition's same ObjectiveEngine. An absolute score difference greater
than `config.global_search.score_tolerance` raises the existing `RuntimeError`.
No extra incumbent evaluation or replacement objective is introduced.

`GlobalReportResult` now lives in `application/results/global_report_result.py`
and remains a `BaseReportResult`. Its title comes from `warm_start.title`. All
existing metadata keys, including inherited `stable_optimization`, are preserved.
The result exposes the existing score/history/search properties plus
`initial_incumbent_score`, `capacity_prunes`, `seed_prunes`, `stopped_by_limit`,
`elapsed_seconds` and `stop_reason`. There is no public `raw_result` property.
Serialization still uses `BaseReportResult.as_dict()` without extra top-level
keys; GLOBAL details remain in `metadata["global_optimization"]`.

`GlobalRunner` remains a small injectable protocol:

```python
def run(self, *, request, composition, warm_start) -> BaseReportResult:
    ...
```

A caller can supply a fake or alternate runner through
`BalancingApplication(config, global_runner=runner)`. Omitting the argument or
passing None selects the production runner. PREASSIGNED bypasses the runner,
even when GLOBAL is selected. Engine-only runner returns are still rejected.
`GlobalExecutionUnavailableError` remains importable for SCRUM-40 compatibility,
but the normal execution path no longer raises it; GLOBAL now has a default
implementation rather than an absent dependency.

`main()` imports CSV data, builds the request and calls the service once. GLOBAL
console output consumes `GlobalReportResult`; no raw search result is retained by
the entrypoint. Factory/metrics/GLOBAL compatibility wrappers and config aliases
have been removed. Characterization uses the real factories and
`ApplicationGlobalRunner`, including optimizer substitution for score rejection.

The composition-retention callback has been removed from bootstrap. Reporting
constructs its own configured scoring model and `HtmlExporterV2` through
`configuration.reporting_factory`, without constructing another engine graph.
FACEIT, bootstrap, console and export remain at the entrypoint. The service itself
performs no file import or export. Its existing injectable composition factory
remains available for isolated application tests and callers.

Tests reuse SCRUM-37 fixtures/fingerprints for FAST/STABLE, compare scores,
metadata, restrictions and history excluding elapsed time, and exercise mode
isolation, custom config, GLOBAL delegation/error handling, PREASSIGNED in all
modes, request snapshots and real entrypoint integration. GLOBAL tests reuse the
SCRUM-37 retention/improvement fingerprints, verify incumbent and objective
identity, score tolerance, metric proxies and serialization. A subprocess rejects
imports of `main` while executing real GLOBAL through the default application.

SCRUM-41 moved production GLOBAL execution into application without changing
the request/result boundary. SCRUM-42 completes the thin entrypoint;
engine hardening remains v0.8 and CLI remains v0.9. Existing restart-validation
differences, GLOBAL flag behavior and player/history identity semantics are
unchanged. Release preparation and the final v0.7 release remain separate work.
