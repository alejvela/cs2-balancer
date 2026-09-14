# Public balancing application API (SCRUM-40)

Baseline: `dc4532bb699b8f687f58eec613e0afc4d631886d` (SCRUM-39).

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
gets fresh scoring, objective, generators and optimizers. FAST → STABLE → FAST
on one service does not mutate a shared balancer mode or retain optimizer state.
The optional `composition_factory` callable must preserve this fresh-graph
contract. Tests and the entrypoint can use it to observe the exact run graph.

PREASSIGNED continues to be detected from `player.team_number`. It returns the
existing evaluation result, preserves teams and bypasses optimization regardless
of requested optimization mode. GLOBAL therefore needs no runner for PREASSIGNED.

## GLOBAL transition until SCRUM-41

`GlobalRunner` is a small protocol with one method:

```python
def run(self, *, request, composition, warm_start) -> BaseReportResult:
    ...
```

Inject it via `BalancingApplication(config, global_runner=runner)`. For optimized
GLOBAL requests the composition still configures `LanBalancer` as STABLE. The
application obtains that warm start and delegates to the runner, forwarding the
same request and composition. It returns the runner's report object directly.
A runner returning an engine-only object is rejected with `TypeError`.

Without a runner, an optimized GLOBAL request raises
`GlobalExecutionUnavailableError` explaining that the execution dependency is
missing. This happens before warm-start optimization, after detecting the report
mode. GLOBAL is a supported request mode whose implementation is injected during
this transition; it is not yet fully migrated.

`main.LegacyGlobalRunner` is the temporary production adapter. It calls the
existing `run_global_optimization()` using the run composition's config and shared
objective/scoring. Legacy calls without config retain their existing wrappers.
The adapter returns only `BaseReportResult` and keeps raw search details solely
at the entrypoint for console output. Metrics adaptation, global search, fresh
objective verification, metadata and `GlobalReportResult` remain in `main.py`.
There is no import from application code back to `main`.

`main()` imports CSV data, builds the request and calls the service once. A small
composition callback retains that run's collaborators for export/reporting,
avoiding a second engine graph. FACEIT, bootstrap, console and export handling
remain at the entrypoint. The service itself performs no file import or export.

Tests reuse SCRUM-37 fixtures/fingerprints for FAST/STABLE, compare scores,
metadata, restrictions and history excluding elapsed time, and exercise mode
isolation, custom config, GLOBAL delegation/error handling, PREASSIGNED in all
modes, request snapshots and real entrypoint integration. A subprocess rejects
imports of `main` while importing and executing the application API.

SCRUM-41 will move the GLOBAL runner implementation into application without
changing the request/result boundary. SCRUM-42 owns the final thin entrypoint;
engine hardening remains v0.8 and CLI remains v0.9. Existing restart-validation
differences, GLOBAL flag behavior and player/history identity semantics are
unchanged. This ticket does not declare v0.7 complete.
