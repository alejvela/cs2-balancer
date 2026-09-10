"""Small reviewed v0.6 outputs through the real main.py composition.

Only search budgets are reduced, using the existing acceptance STABLE config.
Production budgets are protected separately by the composition contract.
"""

from dataclasses import replace
from types import SimpleNamespace

import pytest

import main
from application.results.report_mode import ReportMode
from optimizer.modes.optimization_mode import OptimizationMode
from tests.acceptance.test_engine_acceptance import (
    assert_application_score_consistency,
    assert_shared_invariants,
    canonical_membership,
    stable_config,
    synthetic_players,
)

FAST_TEAMS = (
    (1, 7, 15, 17, 20),
    (2, 5, 6, 14, 18),
    (3, 8, 12, 13, 16),
    (4, 9, 10, 11, 19),
)
STABLE_TEAMS = (
    (1, 7, 9, 19, 20),
    (2, 5, 10, 11, 14),
    (3, 8, 12, 13, 16),
    (4, 6, 15, 17, 18),
)
GLOBAL_TEAMS = (
    (1, 3, 14, 19, 20),
    (2, 4, 6, 17, 18),
    (5, 8, 10, 11, 12),
    (7, 9, 13, 15, 16),
)


def expected_membership(numbers):
    return tuple(tuple(f"SYNTHETIC-{n:04d}" for n in team) for team in numbers)


@pytest.fixture
def composed_run(monkeypatch):
    monkeypatch.setattr(main, "STABLE_OPTIMIZATION_CONFIG", stable_config())
    monkeypatch.setattr(
        main,
        "GLOBAL_OPTIMIZATION_CONFIG",
        replace(
            main.GLOBAL_OPTIMIZATION_CONFIG,
            maximum_nodes=500,
            maximum_evaluations=50,
            maximum_elapsed_seconds=None,
        ),
    )

    def run(mode):
        monkeypatch.setattr(main, "OPTIMIZATION_MODE", mode)
        scoring = main.create_scoring_model()
        objective = main.create_objective_engine(scoring)
        balancer = main.create_balancer(scoring, objective)
        players = synthetic_players()
        result = balancer.run_players(players, 4, metadata={"contract": "SCRUM-37"})
        return players, scoring, objective, result

    return run


@pytest.mark.parametrize(
    "mode,teams,initial,score,components",
    [
        (
            OptimizationMode.FAST,
            FAST_TEAMS,
            85.90274787398944,
            98.82055970041648,
            (
                99.41148754401468,
                92.720168642084,
                100.0,
                99.36112343500005,
                100.0,
                100.0,
            ),
        ),
        (
            OptimizationMode.STABLE,
            STABLE_TEAMS,
            81.92748970563993,
            92.78213695058761,
            (
                99.65926811649504,
                65.02496060444992,
                45.3,
                96.01021713035173,
                100.0,
                100.0,
            ),
        ),
    ],
)
def test_composed_application_output(
    composed_run, mode, teams, initial, score, components
):
    players, _, objective, result = composed_run(mode)
    fresh = assert_shared_invariants(players, result.teams, objective)
    assert_application_score_consistency(result, fresh)
    assert canonical_membership(result.teams) == expected_membership(teams)
    assert result.initial_score == pytest.approx(initial, rel=0, abs=1e-6)
    assert result.final_score == pytest.approx(score, rel=0, abs=1e-6)
    names = (
        "Power Balance",
        "ELO Balance",
        "ELO Spread",
        "KD Balance",
        "Team Size",
        "Seed 1 Separation",
    )
    assert {name: r.score for name, r in result.restrictions.items()} == pytest.approx(
        dict(zip(names, components, strict=True)),
        rel=0,
        abs=1e-6,
    )
    assert result.mode is ReportMode.OPTIMIZED
    assert result.optimized is True
    assert result.evaluation_only is False
    assert result.metadata["optimization_mode"] == mode.value
    # FAST currently advertises False even though this particular pipeline is repeatable.
    assert result.metadata["optimization_deterministic"] is (
        mode is OptimizationMode.STABLE
    )
    assert result.metadata["contract"] == "SCRUM-37"
    if mode is OptimizationMode.STABLE:
        stable = result.metadata["stable_optimization"]
        assert stable["completed_restarts"] == 3
        assert stable["stop_reason"] == "restart_limit"
        _, _, _, replay = composed_run(mode)
        assert canonical_membership(replay.teams) == canonical_membership(result.teams)
        assert replay.final_score == pytest.approx(score, rel=0, abs=1e-6)


@pytest.mark.parametrize(
    "node_budget,teams,score,stop_reason",
    [
        (1, STABLE_TEAMS, 92.78213695058761, "NODE_LIMIT"),
        (500, GLOBAL_TEAMS, 94.43911302364742, "EVALUATION_LIMIT"),
    ],
)
def test_global_orchestration_and_report_contract(
    composed_run,
    monkeypatch,
    node_budget,
    teams,
    score,
    stop_reason,
):
    players, scoring, objective, warm_start = composed_run(OptimizationMode.GLOBAL)
    assert warm_start.metadata["optimization_mode"] == "stable"
    monkeypatch.setattr(
        main,
        "GLOBAL_OPTIMIZATION_CONFIG",
        replace(
            main.GLOBAL_OPTIMIZATION_CONFIG,
            maximum_nodes=node_budget,
        ),
    )
    result, search = main.run_global_optimization(
        players, scoring, objective, warm_start
    )
    fresh = assert_shared_invariants(players, result.teams, objective)
    assert_application_score_consistency(result, fresh)
    assert canonical_membership(result.teams) == expected_membership(teams)
    assert result.final_score == pytest.approx(score, rel=0, abs=1e-6)
    assert result.initial_score == pytest.approx(92.78213695058761, rel=0, abs=1e-6)
    assert result.improvement == pytest.approx(score - result.initial_score, abs=1e-6)
    assert result.mode is ReportMode.OPTIMIZED
    assert result.optimized is True
    assert result.evaluation_only is False
    assert result.history == ()
    assert result.iterations == 0
    assert result.total_evaluations == search.complete_solutions_evaluated
    assert result.metadata["contract"] == "SCRUM-37"
    assert result.metadata["optimization_mode"] == "global"
    assert result.metadata["optimization_deterministic"] is True
    assert (
        result.metadata["stable_optimization"]
        == warm_start.metadata["stable_optimization"]
    )
    assert warm_start.metadata["optimization_mode"] == "stable"
    metadata = result.metadata["global_optimization"]
    assert metadata["stop_reason"] == stop_reason
    assert metadata["stopped_by_limit"] is True
    assert metadata["optimality_proven"] is False
    for key in (
        "nodes_visited",
        "complete_solutions_evaluated",
        "pruned_nodes",
        "capacity_prunes",
        "seed_prunes",
        "bound_prunes",
    ):
        assert metadata[key] == getattr(search, key)
    assert metadata["final_score"] == search.score == result.final_score
    assert metadata["initial_incumbent_score"] == result.initial_score
    # No timing or exact traversal-counter snapshot. The engine unit suite owns
    # counter semantics; this test protects their application-level adaptation.
    if node_budget == 1:
        assert result.total_evaluations == 0
        assert result.improvement == 0


def test_global_application_rejects_inconsistent_final_score(composed_run, monkeypatch):
    players, scoring, objective, warm_start = composed_run(OptimizationMode.GLOBAL)
    # Isolate the application's extra verification from the engine's own check.
    inconsistent = SimpleNamespace(
        teams=warm_start.teams, score=warm_start.final_score + 1
    )
    monkeypatch.setattr(
        main,
        "create_global_optimizer",
        lambda **kwargs: SimpleNamespace(
            optimize=lambda **kwargs: inconsistent,
        ),
    )
    with pytest.raises(RuntimeError, match="GLOBAL devolvió un score inconsistente"):
        main.run_global_optimization(players, scoring, objective, warm_start)


def test_global_currently_ignores_inactive_config_switches(composed_run, monkeypatch):
    players, scoring, objective, warm_start = composed_run(OptimizationMode.GLOBAL)
    baseline_config = main.GLOBAL_OPTIMIZATION_CONFIG
    # These fields exist but do not control the v0.6 search. Deliberately do not
    # turn their names into promised behavior; making them effective is v0.8 work.
    for field, value in (
        ("use_incumbent", False),
        ("use_seed_pruning", False),
        ("use_capacity_pruning", False),
        ("use_power_bound", False),
        ("use_elo_bound", True),
        ("deterministic", False),
        ("base_seed", 7),
    ):
        monkeypatch.setattr(
            main,
            "GLOBAL_OPTIMIZATION_CONFIG",
            replace(
                baseline_config,
                **{field: value},
            ),
        )
        report, search = main.run_global_optimization(
            players, scoring, objective, warm_start
        )
        assert canonical_membership(report.teams) == expected_membership(
            GLOBAL_TEAMS
        ), field
        assert report.final_score == pytest.approx(
            94.43911302364742, rel=0, abs=1e-6
        ), field
        assert report.initial_score == warm_start.final_score, field
        assert search.stop_reason == "EVALUATION_LIMIT", field
        assert search.optimality_proven is False, field
        # The adapter advertises the enum property, not the configuration field.
        assert report.metadata["optimization_deterministic"] is True, field
