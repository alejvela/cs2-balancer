# SCRUM-46 foundation contracts

Implementation contract: [Jira SCRUM-46, comment 10734](https://alevelara.atlassian.net/browse/SCRUM-46?focusedCommentId=10734).
Base: `2fb6a2c7248387538f89d2a040fa94601034e949` (published v0.7.0).

## Numeric boundaries

`models.numeric.finite_real` rejects bool/non-Real values with `TypeError`,
and NaN, either infinity, or values that overflow float conversion with
`ValueError`. It never substitutes, clamps or sanitizes non-finite values.
This small primitive lives in the existing packaged model layer; the legacy
`core` directory is not included by setuptools package discovery.

- `RestrictionResult`: validate score, penalty and weight before existing
  finite range rules; revalidate operands and product for weighted score,
  and penalty for `passed`.
- `ObjectiveResult`: validate initial/final score, mutable restriction numbers
  on addition and before computation (including zero-weight shortcuts),
  aggregation inputs/totals and the weighted-average result. Overflow is an
  error before final clamping. Finite clamping, weighting, subtraction and
  zero-weight behavior remain unchanged.
- GLOBAL: validate metric inputs, immutable team sums (including assignment
  overflow), numeric search/ordering/bound configuration and comparison inputs.
  Validate ordering population totals/influence and bound weight totals,
  weighted aggregation, interval values and result values. These checks do not
  alter bound formulas, proof rules, pruning flags, budget or counter semantics.

## Identity and structure

`models.player_identity.logical_player_identity` is extracted from v0.7
`SolutionSignature`; `SolutionSignature.player_identity` delegates to it.
The exact priority remains explicit `identity`, then `steam_id`, then
`nickname` (or `nick` only when `nickname` is absent), then the same ordered
structural fallback. Text normalization, prefixes (including the existing
`identity:steam:` / `identity:nick:` prefixes), float precision and fallback
field order are preserved. No instance address participates in logical identity.

GLOBAL ordering/root/problem pool validation uses that same authority. Previously
GLOBAL could admit two players with the same explicit identity when their Steam
IDs differed. A focused test now rejects that inconsistent pool. Direct problem
construction also enforces logical uniqueness.

`GlobalPlayerMetrics.identity` remains the v0.7 **ordering key**, preserving its
tuple shape and named-player tie behavior. It is no longer used for pool
uniqueness. Its anonymous nickname fallback previously used `id(player)`;
equivalent fresh anonymous objects now receive the shared stable identity.
This demonstrated anonymous-player bug is covered explicitly.

Duplicate structural checks are deliberately narrow:

- Signature construction rejects the same mutable `Team` instance twice,
  including empty teams. Equal team labels on distinct objects remain legal.
- Signature construction retains logical player uniqueness, whether duplicates
  are the same object or separate equivalent objects.
- GLOBAL immutable state rejects repeated player indices within or across teams.
  Sharing an empty immutable team state remains legal.

Moves, transactional snapshots, restoration and exact player references retain
instance identity. No Local/STABLE validation or transaction redesign is included.

## Legacy audit

Repository-wide source, tests and composition were inspected:

- `Neighborhood.generate()`: no production consumer; all three concrete
  neighborhoods enumerate through `iterate()` and `sample()`. The v0.7 tests in
  `tests/unit/optimizer/neighborhoods/test_neighborhood.py` explicitly require
  inherited `generate()` to return `None`, including sample-only subclasses.
  Preserve that tested compatibility hook and document it; do not make it
  abstract or add an algorithm. Existing contract tests remain unchanged.
- `MoveSource`: its file was the only reference to the class/module. It imported
  nonexistent `optimizer.optimizers.swap`, and imported the `random` function
  while calling module methods on it. No composition, strategy, neighborhood,
  export or test consumed it. Delete this unimportable dead abstraction; do not
  replace it. Supported enumeration interfaces are unchanged.
- `DoubleSwapMove`: used by `DoubleSwapNeighborhood`, wired by the pipeline
  factory and exercised by move/neighborhood tests. Preserve `first_swap` and
  `second_swap`, four-distinct-instance checks, application/undo and rollback
  behavior. No demonstrated invariant requires hiding the accessors. Existing
  restoration and failure tests remain unchanged.

## Deferred work and validation limits

SCRUM-47 retains transaction failure precedence; SCRUM-48 retains restart
semantics; SCRUM-49 retains incumbent compatibility and flags; SCRUM-50 retains
proof/bound semantics; SCRUM-51 retains budgets/counters. This change does not
claim to resolve them. A future compatibility cleanup may rename the legacy
GLOBAL `identity` ordering-key API or retire `Neighborhood.generate()`; neither
is necessary for this foundation contract.

No application/composition, CLI/YAML, reporting, importer, analytics, scoring,
weights, normalization or tuning changes are included. Frozen v0.7 fixtures and
fingerprints are not edited. Full acceptance/regression tests verify their
unchanged observable outputs.

The default `python main.py` bootstrap requires FACEIT import credentials;
the offline smoke invocation exits with the existing missing-key error. No
FACEIT request is made. The suite exercises supported application/bootstrap
flows using frozen data and mocks. Validation totals and coverage are recorded
in the PR description.
