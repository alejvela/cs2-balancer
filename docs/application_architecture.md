# Balancing application architecture

SCRUM-43 consolidates the application foundation implemented through SCRUM-41,
on baseline `074e769e8d68ad7e20cbbe7a97cb98c27b7cf30b`. This is acceptance and
architecture documentation, not a final v0.7 release declaration. SCRUM-42
completes the thin production entrypoint on SCRUM-43 merge
`4ca5a370bef548b2b8ca835b6b8bce8e1f4ba3ba`.

## Purpose and boundaries

v0.7 is a **behavior-preserving application foundation**:

> v0.7 changes where production composition and orchestration live,
> not how balancing scores or teams are calculated.

The production defaults, scoring, objective, pipeline, team selection, metadata,
restart semantics and bounded GLOBAL behavior retain the SCRUM-37 characterization
of v0.6. Reduced acceptance budgets make deterministic tests practical; they do
not redefine production budgets or promise a full-budget solution fingerprint.

| Boundary | Responsibility |
| --- | --- |
| `ApplicationConfig` | Immutable typed Python configuration; production defaults and explicit customization |
| Factories in `configuration/` | Construct scoring, objective, pipeline, optimizers and GLOBAL search structures from explicit inputs |
| `create_balancing_composition` | Wire a fresh `BalancingComposition`: config, scoring model, objective engine and balancer |
| `BalancingApplication` | Own request execution, fresh composition and default GLOBAL orchestration |
| `BalancingRequest` | Runtime players, team count, optimization mode, optional title and metadata |
| Engine collaborators | Generate, evaluate and optimize teams with existing algorithms |
| `BaseReportResult` | Public report contract consumed by callers, console helpers and HTML export |

The execution dependency direction is:

```text
main
  -> application service
    -> configuration / composition
      -> engine collaborators
```

Neither application nor configuration/composition imports `main`. This is a
responsibility diagram, not a prohibition on every cross-package import: the
composition root constructs `application.lan_balancer.LanBalancer`, and exporters
consume application result types. Engines do not depend on entrypoint bootstrap,
CLI or live data acquisition. Existing subprocess tests reject imports of `main`
during composition, public application execution and real default GLOBAL execution.

## Configuration and public use

```python
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from configuration.application_config import ApplicationConfig
from optimizer.modes.optimization_mode import OptimizationMode

config = ApplicationConfig.production_defaults()
app = BalancingApplication(config)
# players is a Sequence[Player] supplied by the caller.
result = app.run(
    BalancingRequest(
        players=players,
        number_of_teams=4,
        optimization_mode=OptimizationMode.STABLE,
    )
)
print(result.final_score, result.summary())
```

Customize frozen values with `dataclasses.replace` before constructing the
application. Typed Python config is the production source of truth. There is no
YAML loader or external configuration framework. The request overrides execution
mode and team count for that run; team size and tuning remain config inputs.
The service performs no CSV import, FACEIT request or file export.

Every `run` calls the composition factory once. Fresh scoring, objective,
generators, optimizers, evaluators and pipelines prevent residual optimizer state
from leaking across FAST → STABLE → GLOBAL → FAST. A supplied composition factory
must honor the same lifecycle. Immutable config can be shared; the frozen
composition holder does not make its engine collaborators immutable.

The request snapshots the player sequence as a tuple and metadata as a read-only
top-level mapping. Each execution gets its own metadata dict. Player objects and
nested metadata values retain their existing references; this is not deep-copy
isolation or a new Player identity guarantee.

## Execution and acceptance matrix

All rows return `BaseReportResult`. Concrete types retain their own semantics.

| Flow | Public request | Engine path | Public result | SCRUM-43 acceptance |
| --- | --- | --- | --- | --- |
| PREASSIGNED | `BalancingRequest` with assigned players, any requested mode | Preassigned generation + evaluator | `EvaluationResult` | `test_preassigned_acceptance_ignores_global_optimization` |
| FAST | `BalancingRequest(..., optimization_mode=OptimizationMode.FAST)` | Snake draft + local pipeline | `OptimizationResult` | `test_public_flow_preserves_characterized_report[FAST]` |
| STABLE | `BalancingRequest(..., optimization_mode=OptimizationMode.STABLE)` | Snake draft + deterministic multi-start local optimization | `OptimizationResult` | `test_public_flow_preserves_characterized_report[STABLE]` |
| GLOBAL | `BalancingRequest(..., optimization_mode=OptimizationMode.GLOBAL)` | STABLE warm start + bounded GLOBAL search + verification | `GlobalReportResult` | `test_public_flow_preserves_characterized_report[GLOBAL]` |

The parameter labels above identify modes, rather than literal pytest node IDs.
These tests live in
[`test_v07_application_acceptance.py`](../tests/acceptance/test_v07_application_acceptance.py).

FAST generates the initial composition and runs the configured local phases.
STABLE uses the configured deterministic restart generator and local optimizer,
selects the existing result and preserves `stable_optimization` metadata,
restart count, stop reason and history behavior. Acceptance reuses existing
canonical memberships and report comparisons, including scores, penalty,
restriction scores, evaluations and history, excluding elapsed time.

GLOBAL runs through the default executor without runner injection:

```text
BalancingApplication
  -> LanBalancer configured internally as STABLE
  -> warm start
  -> ApplicationGlobalRunner
  -> GLOBAL factories and GlobalOptimizer
  -> verification with the composition's ObjectiveEngine
  -> GlobalReportResult
```

The runner adapts player metrics, passes the warm-start teams and final score as
incumbent unchanged, runs bounded search and reevaluates the selected teams with
the same objective. A score mismatch beyond configured tolerance raises the
existing error. It preserves STABLE metadata and adds `global_optimization`,
including search counters, stop reason, limit and proof flags. Acceptance checks
the characterized improvement scenario, incumbent score and public counter
mapping; SCRUM-41 also protects incumbent retention and verification failure.
Elapsed time is reported but never compared exactly. These tests do not introduce
a new proof guarantee or change bound admissibility.

PREASSIGNED is a report mode detected from player assignments, separate from the
requested optimization mode. It preserves assigned membership, evaluates only,
and bypasses both local optimization and the GLOBAL runner. The representative
SCRUM-43 request selects GLOBAL; SCRUM-40 already covers all requested modes.

## Results and consumers

Callers work against `BaseReportResult`: teams, objective scores, initial/final
score, improvement, penalty, restrictions, report mode, metadata, execution/history
properties, `summary()` and `as_dict()`. There is no new unified concrete result.
GLOBAL exposes public search metrics, including `initial_incumbent_score`,
`nodes_visited`, `complete_solutions_evaluated`, pruning counters, `stop_reason`,
`stopped_by_limit` and `optimality_proven`. Serialization retains the common
schema, with search details inside metadata. Callers need no
`GlobalOptimizationResult` or `StableOptimizationRun`.

`HtmlExporterV2.export(result, output)` consumes the common contract and returns
the written `Path`. Acceptance exports real FAST, STABLE, GLOBAL and PREASSIGNED
reports into temporary directories and checks the path, HTML markers, report
mode and player content without a whole-HTML snapshot. Export leaves the report
serialization unchanged. The exporter uses its configured presentation title
(`EventConfig.report_title` in the composition); a request title remains the
result's title and does not override that exporter setting.

## Supported entrypoint

`python main.py` remains supported in v0.7. `main.py` is an entrypoint; the reusable
application API is `BalancingApplication`.

`main` retains file resolution, optional FACEIT refresh, CSV import, roster/result
integrity checks, request construction, console presentation, HTML export and
existing error/exit handling. It creates one local `ApplicationConfig` from
`production_defaults()` and calls `BalancingApplication.run()` once. FAST, STABLE,
GLOBAL and PREASSIGNED all use that path; mode detection belongs to `LanBalancer`.
The mode banner is printed from the returned report, after execution. Its text
is unchanged; failed execution no longer prints a speculative mode banner.
Bootstrap adds the detected `mode` to report metadata before presentation/export,
preserving the exported metadata without detecting PREASSIGNED itself.

The entrypoint has no engine factories, GLOBAL forwarding wrappers, config aliases
or composition-retention callback. `configuration.reporting_factory` constructs
only a fresh configured scoring model and `HtmlExporterV2` for console/HTML use.
It does not construct an objective, pipeline, optimizer or balancing engine.
Offline tests compare this presentation with the execution composition's exporter
byte for byte, including custom scoring and all result modes. GLOBAL console output
accepts only the public `GlobalReportResult`.

The existing output checks for roster preservation, non-decreasing score and
preassigned membership remain bootstrap checks, with their original errors. They
do not select, generate or evaluate PREASSIGNED teams. The application API and
result contract are unchanged. Characterization calls real factories and
`ApplicationGlobalRunner`, retaining the reviewed membership/score fingerprints.

Offline bootstrap acceptance calls real `main.main()` for FAST and GLOBAL with
fake file resolution and importer data, real application execution and real HTML
export. It asserts one application run, exit code zero and correct report
consumers, and forbids live FACEIT. `test_main_entrypoint.py` additionally protects the
absence of engine factories and a second GLOBAL route, FACEIT config/file flow,
report equivalence, roster rejection and existing error/exit behavior. It does not
run the default live-refresh shell command or require credentials/runtime CSVs.

## Evidence and specialized contracts

| Protection | Test source |
| --- | --- |
| Production defaults and characterized memberships/scores | SCRUM-37 `test_application_composition_contract.py`, `test_application_behavior_contract.py` |
| Immutable config and validation | SCRUM-38 `test_application_config.py` |
| Factories, fresh graphs, explicit custom values and import boundary | SCRUM-39 `test_composition_factories.py`, `test_composition_root.py` |
| Request snapshots, common results, all-mode PREASSIGNED and import boundary | SCRUM-40 `test_balancing_request.py`, `test_balancing_application_api.py` |
| Default GLOBAL, incumbent/verification, metric proxies and serialization | SCRUM-41 `test_global_application_execution.py`, `test_global_execution.py`, `test_global_report_result.py` |
| All-mode public fingerprints and real HTML | SCRUM-43 `test_public_flow_preserves_characterized_report`, `test_html_exporter_accepts_common_public_result` |
| Same-service FAST → STABLE → GLOBAL → FAST and STABLE replay | SCRUM-43 `test_fast_stable_global_fast_isolation_and_stable_replay` |
| Two teams of two, custom seed restriction and result title | SCRUM-43 `test_custom_config_reaches_public_result` |
| Offline FAST/GLOBAL bootstrap and common report consumers | SCRUM-43 `test_main_bootstrap_exports_application_result_offline` |

SCRUM-43 reuses the existing synthetic roster, fingerprints, reduced budgets and
report comparison helper rather than introducing another set of score snapshots.
The shared comparison also handles the empty tuple history of GLOBAL/evaluation
results while retaining local history checks. Frozen LAN regression and tournament
acceptance remain independent protections in the full suite.

Specialized documentation:

- [SCRUM-37 historical behavior contract](application_foundation_contract.md)
- [Typed application configuration](typed_application_configuration.md)
- [Composition factories and root](composition_root.md)
- [Public request/result API and GLOBAL details](balancing_application_api.md)

## Deferred work

v0.7 does not tune scoring, redesign engines, introduce CLI/YAML configuration or
fix GLOBAL proof behavior. SCRUM-43 changes tests and documentation only. Release
metadata, version changes, tags and publication belong to SCRUM-44/SCRUM-45.

v0.8 owns engine contract hardening, including these preserved debts:

- **GLOBAL ignored flags:** supplied incumbents are consumed despite
  `use_incumbent=False`; some pruning/bound switches do not gate current bound
  calculation, and deterministic/base-seed settings do not control traversal.
  Symmetry breaking is active. Mode-derived deterministic metadata is unchanged.
- **Proof semantics:** existing exhaustion/optimality flags need their own
  contract review; application acceptance is not a mathematical proof.
- **Incumbent validation:** preserve current verification and preconditions;
  strengthening identity, feasibility or score validation requires engine work.
- **Bounds admissibility:** retain current optimistic bounds and assumptions;
  stronger admissibility guarantees require separate analysis and tests.
- **Timing/budget semantics:** limit priority, counters and elapsed-time scope
  remain unchanged; no new end-to-end budget guarantee is introduced.
- **Player identity:** existing identity/reference semantics remain intact.
- **MoveEvaluator transaction safety:** exception-safe mutation/rollback
  guarantees require separate engine hardening.
- **Restart/result semantics:** existing STABLE history/result consistency and
  restart validation differences remain, including the zero minimum-swaps
  config accepted as data but rejected by the restart generator.

v0.9 owns CLI and operator UX. v1.0 targets the stable toolkit. This document
records the implemented foundation and remaining boundaries without declaring
those future contracts complete.
