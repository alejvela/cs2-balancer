# Typed application configuration (SCRUM-38, adopted by SCRUM-39)

`ApplicationConfig.production_defaults()` in
`configuration/application_config.py` returns fresh, frozen/slotted Python value
objects. It preserves the production contract at
`5731957d26ce0b46077621bbad750cfe5bb10227` (SCRUM-37, PR #25).
There is no runtime file loader or new dependency.

The application object contains `EventConfig`, `PathsConfig`, `FaceitConfig`,
`ScoringConfig`, `ObjectiveConfig`, `PipelineConfig`, `RestartConfig`, the two
existing optimizer configs, the optimization mode and debug switches.
Scoring owns a tuple of `ScoringComponentConfig`; pipeline owns a tuple of
`PhaseConfig`. All these objects contain data, never mutable engine instances.

Scoring components declare names, attributes, weights and logistic parameters.
Objective declares the six restriction weights and parameters. Team size comes
from the event, and expected player count is derived from team count and size.
Pipeline declares swap neighborhoods and first-improvement/exhaustive strategies
with their phase parameters. Factories in `configuration/` create concrete
collaborators from explicit config inputs; see [composition root](composition_root.md).

`StableOptimizationConfig` and `GlobalOptimizationConfig` are already immutable
value types with validation. They are reused directly, with explicit production
arguments in default factories; their constructors and engine defaults are
unchanged. Their restart/node/evaluation/time validation remains authoritative.
Restart generator parameters are separate data because the generator is mutable.
Snake draft uses the same seed settings as restart generation. GLOBAL ordering
and root seed protection use the objective's seed settings.

Activity configuration explicitly selects `engine_defaults`. `ActivityFactorModel`
remains the sole owner of its targets, weights, level strength mapping and minimum
factor. The scoring factory creates a fresh model for each scoring model. SCRUM-37 tests
freeze those values; duplicating the mapping here would create avoidable drift.

`ApplicationConfig.production_defaults()` supplies the production source of truth.
`main.APPLICATION_CONFIG` and its derived aliases preserve the entrypoint contract,
including the identical STABLE/GLOBAL objects. Factories accept explicit config
arguments and do not import `main`. GLOBAL bound weights read the objective weights,
and its tolerance reads the GLOBAL config. No duplicate bound config is needed.
GLOBAL orchestration and `GlobalReportResult` remain in `main.py`.

Validation covers positive event dimensions and phase iterations; nonnegative
weights and FACEIT limits; unique scoring/phase names; a nonempty pipeline;
supported declarative strategies/neighborhood/activity policy; ordered,
nonnegative swap limits and redistribution ratios in [0, 1]. Sequence inputs are
copied to tuples to prevent mutation through a caller-owned list.

This is not a general engine hardening layer. It does not require weights to sum
to 100, positive individual weights, an enabled phase, existing paths, a fixed
player count, finite search limits, or a particular seed/score range. It does not
duplicate all constructor-specific validation of restriction/strategy classes.
Existing engine config validation is neither relaxed nor strengthened. Some
typed configurations can therefore still be rejected during engine construction.

The legacy aliases are captured at import time; replacing `APPLICATION_CONFIG`
at runtime is not a supported application configuration API. Call
`create_balancing_composition(config)` for explicit composition. Compatibility
wrappers in `main.py` translate legacy aliases into a config snapshot. Ignored
GLOBAL flags and warm-start/report behavior remain unchanged.

Unit tests cover defaults, derived values, frozen nested objects, sequence copies,
default-factory isolation, independent mutable collaborators and validation.
The untouched SCRUM-37 acceptance tests remain the independent behavioral guard.
Coverage now includes the `configuration` package.
