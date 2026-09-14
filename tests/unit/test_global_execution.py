"""Preserve incumbent identity, final verification and player adaptation."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from application.balancing_request import BalancingRequest
from application.global_execution import ApplicationGlobalRunner, create_global_metrics
from configuration import global_factory
from configuration.composition_root import create_balancing_composition
from objective.objective_engine import ObjectiveEngine
from optimizer.global_search.global_optimization_result import GlobalOptimizationResult
from optimizer.modes.optimization_mode import OptimizationMode
from tests.unit.test_composition_root import players, small_config


def test_metrics_preserve_player_identity_fallbacks_and_numeric_conversion():
    primary = SimpleNamespace(elo=1600, faceit_elo=999, kd=1.2, seed=None)
    fallback = SimpleNamespace(elo=None, faceit_elo="1700", kd="1.3", seed="2")
    calls = []

    def power(player):
        calls.append(player)
        return "42.5"

    metrics = create_global_metrics(
        iter([primary, fallback]), SimpleNamespace(power=power)
    )
    assert isinstance(metrics, tuple)
    assert calls == [primary, fallback]
    assert metrics[0].player is primary and metrics[1].player is fallback
    assert [(m.power, m.elo, m.kd, m.seed) for m in metrics] == [
        (42.5, 1600.0, 1.2, None),
        (42.5, 1700.0, 1.3, 2),
    ]


@pytest.mark.parametrize(
    "player,message",
    [
        (
            SimpleNamespace(nickname="Primary", nick="Fallback", kd=1.0),
            "Primary no contiene ELO",
        ),
        (SimpleNamespace(nick="Fallback", elo=1500), "Fallback no contiene KD"),
        (SimpleNamespace(kd=1.0), "Unknown no contiene ELO"),
    ],
)
def test_metrics_keep_existing_missing_stat_errors(player, message):
    with pytest.raises(ValueError, match=message):
        create_global_metrics([player], SimpleNamespace())


@pytest.mark.parametrize("delta,raises", [(0, False), (0.25, False), (0.5, True)])
def test_incumbent_and_shared_objective_verification_are_exact(
    monkeypatch, delta, raises
):
    config = small_config()
    config = replace(
        config,
        optimization_mode=OptimizationMode.GLOBAL,
        global_search=replace(config.global_search, score_tolerance=0.25),
    )
    composition = create_balancing_composition(config)
    request = BalancingRequest(
        players(),
        2,
        OptimizationMode.GLOBAL,
        title="Warm title",
        metadata={"caller": "kept"},
    )
    warm = composition.balancer.run_players(
        request.players, 2, title=request.title, metadata=request.metadata
    )
    original_metadata = dict(warm.metadata)
    evaluations = []
    original_evaluate = ObjectiveEngine.evaluate

    def evaluate(self, teams):
        evaluations.append((self, teams))
        return original_evaluate(self, teams)

    raw = GlobalOptimizationResult(
        teams=warm.teams,
        score=warm.final_score + delta,
        initial_incumbent_score=warm.final_score,
        nodes_visited=7,
        complete_solutions_evaluated=3,
        pruned_nodes=4,
        capacity_prunes=1,
        seed_prunes=1,
        bound_prunes=2,
        elapsed_seconds=1.25,
        optimality_proven=False,
        stopped_by_limit=True,
        stop_reason="NODE_LIMIT",
    )

    class Optimizer:
        def optimize(self, *, problem, incumbent_teams, incumbent_score):
            assert evaluations == []  # No fresh incumbent evaluation before search.
            assert incumbent_teams is warm.teams
            assert incumbent_score == warm.final_score
            assert {id(m.player) for m in problem.players} == {
                id(p) for p in request.players
            }
            return raw

    def optimizer_factory(actual_config, objective):
        assert actual_config is config
        assert objective is composition.objective_engine
        return Optimizer()

    monkeypatch.setattr(ObjectiveEngine, "evaluate", evaluate)
    monkeypatch.setattr(global_factory, "create_global_optimizer", optimizer_factory)
    if raises:
        with pytest.raises(
            RuntimeError, match="GLOBAL devolvió un score inconsistente"
        ):
            ApplicationGlobalRunner().run(
                request=request, composition=composition, warm_start=warm
            )
    else:
        result = ApplicationGlobalRunner().run(
            request=request, composition=composition, warm_start=warm
        )
        assert (
            result.final_score == warm.final_score
        )  # Fresh objective remains authoritative.
        assert result.metadata["global_optimization"]["final_score"] == raw.score
        assert result.title == "Warm title"
        assert result.metadata["caller"] == "kept"
        assert (
            result.metadata["stable_optimization"]
            == warm.metadata["stable_optimization"]
        )
        assert result.metadata["optimization_applied"] is True
        assert result.metadata["optimization_mode"] == "global"
        assert (
            result.metadata["optimization_mode_label"] == OptimizationMode.GLOBAL.label
        )
        assert (
            result.metadata["optimization_deterministic"]
            is OptimizationMode.GLOBAL.deterministic
        )
        assert result.metadata["global_optimization"] == {
            "initial_incumbent_score": raw.initial_incumbent_score,
            "final_score": raw.score,
            "improvement": raw.improvement,
            "nodes_visited": 7,
            "complete_solutions_evaluated": 3,
            "pruned_nodes": 4,
            "capacity_prunes": 1,
            "seed_prunes": 1,
            "bound_prunes": 2,
            "elapsed_seconds": 1.25,
            "optimality_proven": False,
            "stopped_by_limit": True,
            "stop_reason": "NODE_LIMIT",
        }
    assert len(evaluations) == 1
    assert evaluations[0][0] is composition.objective_engine
    assert evaluations[0][1] is raw.teams
    assert warm.metadata == original_metadata
    assert request.metadata == {"caller": "kept"}
