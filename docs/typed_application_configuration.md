# Typed application configuration (SCRUM-38, adopted by SCRUM-39)

See [application architecture](application_architecture.md) for the current
execution flows, acceptance matrix and deferred work. This document details the
configuration contract; the baseline below is historical.

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
`main()` creates this config locally and passes it explicitly to bootstrap,
application and reporting. Factories accept explicit config arguments and never
import `main`. GLOBAL bound weights read the objective weights, and its tolerance
reads the GLOBAL config. No duplicate bound config is needed. GLOBAL orchestration
and `GlobalReportResult` live in application.

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

Customize the local config construction in `main()` using `dataclasses.replace`
for the supported developer workflow; see the README example. No import-time
aliases or config reconstruction remain. Use `BalancingApplication(config)` for
reusable execution or `create_balancing_composition(config)` for explicit
composition. Ignored GLOBAL flags and warm-start/report behavior remain unchanged.

Unit tests cover defaults, derived values, frozen nested objects, sequence copies,
default-factory isolation, independent mutable collaborators and validation.
SCRUM-37 acceptance tests retain their fingerprints through the real owners.
Coverage now includes the `configuration` package.
