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

`main()` uses the root. Temporary wrappers keep `create_scoring_model`,
`create_objective_engine`, `create_pipeline`, `create_balancer`,
`create_global_problem` and `create_global_optimizer` callable with the SCRUM-37
signatures. `_composition_config()` translates legacy mode, optimizer configs and
event aliases at this boundary, preserving the characterization tests' overrides.
New callers use explicit config rather than these wrappers.

GLOBAL selection still configures `LanBalancer` internally as STABLE. Metrics
adaptation, warm start, search execution, final-score verification, metadata and
`GlobalReportResult` remain in `main.py`. The structural factory can be called
independently with prepared `GlobalPlayerMetrics`; it does not run the search.

Compatibility tests from SCRUM-37 and SCRUM-38 remain unchanged. New tests cover
custom values, graph identity, all three mode selections, independent mutable
instances, a small two-team run, GLOBAL construction/budget and a subprocess that
rejects imports of `main` while composing the system.

Known debt is preserved: `RestartConfig(minimum_swaps=0)` is valid as data but
`DeterministicRestartGenerator` rejects zero during construction. A test records
this existing boundary without weakening either validation. Some GLOBAL flags
remain ignored. `generators/team_generator.py` remains empty and untouched because
the current concrete generators are sufficient for composition.

Remaining scope: common application API = SCRUM-40; GLOBAL orchestration =
SCRUM-41; final thin entrypoint = SCRUM-42; engine hardening = v0.8. No new common
application/result API, optimizer fixes or configuration framework is introduced.
