# Composition factories and root (SCRUM-39)

Baseline: `4a4036919329e14fdc7e9383973ec03898dfb7f4` (SCRUM-38).
This is an incremental v0.7 step; v0.7 is not complete.

```text
ApplicationConfig
       ↓
Factories (explicit typed inputs)
       ↓
Composition Root
       ↓
Engine collaborators
```

```python
from configuration.application_config import ApplicationConfig
from configuration.composition_root import create_balancing_composition

config = ApplicationConfig.production_defaults()
composition = create_balancing_composition(config)
# When player data is available:
# result = composition.balancer.run_players(players, config.event.number_of_teams)
```

Use `dataclasses.replace` to customize the config before composition. The root
does not import `main`, read module aliases, import CSV data, access FACEIT, run
optimization or export a report. Paths and FACEIT bootstrap remain entrypoint
concerns for now.

`BalancingComposition` is a frozen/slotted holder of `config`, `scoring_model`,
`objective_engine` and `balancer`. The local optimizer and its pipeline are
available through `balancer.optimizer`; storing them again adds no capability.
The holder is immutable, but its engine collaborators retain their existing
mutability. Each root call creates a fresh graph; no mutable instance is cached.

Factories:

- `scoring_factory.create_scoring_model(ScoringConfig)` builds attribute components,
  logistic normalizers, weights and a fresh `ActivityFactorModel`. The validated
  `engine_defaults` policy keeps activity defaults in their original owner.
- `objective_factory.create_objective_engine(ObjectiveConfig, scoring_model,
  team_size=...)` builds the original six restrictions in the same order.
- `pipeline_factory.create_pipeline(PipelineConfig)` translates `swap`,
  `first_improvement` and `exhaustive` into fresh neighborhoods/strategies per phase.
- `optimization_factory` builds a local optimizer with its evaluator and pipeline,
  then STABLE with an explicit restart config, selector and shared local optimizer.
- `composition_root.create_balancer(config, scoring_model, objective_engine=None)`
  wires the importer, generators, evaluators, exporter and optimizers. The root
  supplies a shared objective; the helper can create one for legacy callers.
- `global_factory` builds the problem from explicit config and prepared metrics,
  plus the optimizer and bound from config and a shared objective. The bound uses
  objective weights and GLOBAL tolerance; no duplicate defaults are introduced.

`BalancingApplication` uses the root once per request; `main()` now calls that
service and retains the run composition for reporting. See the
[public application API](balancing_application_api.md). Temporary wrappers keep `create_scoring_model`,
`create_objective_engine`, `create_pipeline`, `create_balancer`,
`create_global_problem` and `create_global_optimizer` callable with the SCRUM-37
signatures. `_composition_config()` translates legacy mode, optimizer configs and
event aliases at this boundary, preserving the characterization tests' overrides.
New callers use explicit config rather than these wrappers.

GLOBAL selection still configures `LanBalancer` internally as STABLE. The
application obtains that warm start and its default `ApplicationGlobalRunner`
uses `application/global_execution.py` for metrics adaptation, search execution,
final-score verification and metadata. `GlobalReportResult` lives in
`application/results/`. The structural factory can still be called independently
with prepared `GlobalPlayerMetrics`; it does not run the search. The runner shares
the composition's ObjectiveEngine with STABLE and passes the incumbent unchanged.
`main` retains forwarding wrappers only and prints the application report metrics;
no legacy runner or raw search-result state is needed.

Compatibility tests from SCRUM-37 and SCRUM-38 remain unchanged. New tests cover
custom values, graph identity, all three mode selections, independent mutable
instances, a small two-team run, GLOBAL construction/budget and a subprocess that
rejects imports of `main` while composing the system.

Known debt is preserved: `RestartConfig(minimum_swaps=0)` is valid as data but
`DeterministicRestartGenerator` rejects zero during construction. A test records
this existing boundary without weakening either validation. Some GLOBAL flags
remain ignored. `generators/team_generator.py` remains empty and untouched because
the current concrete generators are sufficient for composition.

SCRUM-40 adds the common application API using the existing `BaseReportResult`.
SCRUM-41 adds production GLOBAL orchestration with no dependency on `main`.
Remaining scope: final thin entrypoint = SCRUM-42; engine hardening = v0.8. No optimizer fixes or configuration framework
are introduced by composition or the application API.
