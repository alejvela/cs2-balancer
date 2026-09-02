# cs2-balancer v0.5.0

Version 0.5.0 is the engine-stabilization baseline for this internal,
developer-oriented application.

## Engine stabilization

- Established `ObjectiveEngine` as the authoritative team-quality score.
- Stabilized the production player scoring model.
- Enforced structural optimizer invariants and fresh final-score reevaluation.

## Optimization

- FAST local optimization from the generated composition.
- Deterministic STABLE multi-start optimization and reproducible selection.
- Advanced bounded GLOBAL search using a verified STABLE warm start.

## Testing

- 408-test v0.5.0 baseline at the start of the release-hygiene ticket.
- Unit coverage for scoring, objective restrictions, moves, neighborhoods, and
  FAST/STABLE/GLOBAL optimizer contracts.
- Synthetic 20-player acceptance coverage across all three optimization modes.
- Frozen LAN 2026 regression coverage, including the 20-player power fingerprint,
  deterministic initial generation, and deterministic STABLE behavior.

## GLOBAL limitations

GLOBAL is an advanced bounded mode externally orchestrated through `main.py`.
Normal limits can stop a run before search exhaustion, so a result does not imply
proof of mathematical optimality unless the solver explicitly establishes proof
under its admissibility and precondition assumptions. Additional GLOBAL contract
and configuration hardening is deferred.

## Known v0.6+ debt

- Centralized typed configuration and composition.
- A common FAST/STABLE/GLOBAL application API.
- GLOBAL validation and configuration hardening.
- Consistent non-finite numeric validation.
- Optimizer transaction and result hardening.
- Direct external-adapter and report coverage.
- A deliberate CLI and application architecture.
- Removal of stale configuration and unused legacy code.

## Install and run status

Python >= 3.11 is required, and `pyproject.toml` is authoritative. This remains a
developer application without a mature CLI. Default application execution
refreshes FACEIT data and requires `FACEIT_API_KEY`; the fully offline test suite
requires neither FACEIT access nor credentials.
