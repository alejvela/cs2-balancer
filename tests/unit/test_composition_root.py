"""A coherent reusable graph without main.py or hidden production defaults."""

import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from configuration import global_factory
from configuration.application_config import (
    ApplicationConfig,
    EventConfig,
    PhaseConfig,
    PipelineConfig,
)
from configuration.composition_root import create_balancer, create_balancing_composition
from configuration.global_factory import create_global_optimizer, create_global_problem
from configuration.scoring_factory import create_scoring_model
from models.player import Player
from optimizer.global_search.global_search_state import GlobalPlayerMetrics
from optimizer.modes.optimization_mode import OptimizationMode


@pytest.mark.parametrize(
    "mode,internal",
    [
        (OptimizationMode.FAST, OptimizationMode.FAST),
        (OptimizationMode.STABLE, OptimizationMode.STABLE),
        (OptimizationMode.GLOBAL, OptimizationMode.STABLE),
    ],
)
def test_production_composition_graph_and_mode_semantics(mode, internal):
    config = replace(ApplicationConfig.production_defaults(), optimization_mode=mode)
    composition = create_balancing_composition(config)
    balancer = composition.balancer
    assert composition.config is config
    assert balancer.optimization_mode is internal
    assert balancer.generator.scoring_model is composition.scoring_model
    assert balancer.exporter.scoring_model is composition.scoring_model
    assert balancer.optimizer.evaluator.objective is composition.objective_engine
    assert (
        balancer.preassigned_evaluator.objective_engine is composition.objective_engine
    )
    assert (
        composition.objective_engine.restrictions[0].scoring_model
        is composition.scoring_model
    )
    assert balancer.stable_optimizer.local_optimizer is balancer.optimizer
    assert balancer.stable_optimizer.config is config.stable
    assert balancer.stable_optimizer.selector.config is config.stable
    assert len(balancer.optimizer.pipeline.phases) == 2
    assert not hasattr(composition, "__dict__")
    with pytest.raises(FrozenInstanceError):
        composition.config = config


def small_config():
    config = ApplicationConfig.production_defaults()
    return replace(
        config,
        event=EventConfig(
            number_of_teams=2,
            team_size=2,
            team_name_prefix="Custom",
            report_title="Custom report",
            preassigned_title="Custom evaluation",
            importer_strict=False,
            require_all_teams=False,
        ),
        scoring=replace(config.scoring, minimum_available_weight=10, default_power=11),
        objective=replace(config.objective, kd_max_deviation=0.6, seed_level=2),
        restart=replace(
            config.restart,
            separated_seed_level=2,
            maximum_seeded_players_per_team=2,
            minimum_swaps=1,
            maximum_swaps=2,
            partial_redistribution_ratio=0.25,
        ),
        pipeline=PipelineConfig(phases=(PhaseConfig("Short", "exhaustive", 2),)),
        stable=replace(
            config.stable,
            maximum_restarts=2,
            minimum_restarts=1,
            convergence_patience=1,
            minimum_unique_solutions=0,
            target_confirmation_restarts=1,
            base_seed=7,
        ),
        global_search=replace(
            config.global_search, maximum_nodes=1, maximum_elapsed_seconds=None
        ),
        optimization_mode=OptimizationMode.FAST,
    )


def players():
    return [
        Player(
            nick=f"P{i}",
            steam_id=f"CUSTOM-{i}",
            elo=1400 + i * 100,
            kd=0.9 + i * 0.1,
            seed=2 if i == 0 else None,
        )
        for i in range(4)
    ]


def test_custom_config_reaches_collaborators_and_runs_small_event():
    config = small_config()
    composition = create_balancing_composition(config)
    balancer = composition.balancer
    assert balancer.importer.strict is False
    assert balancer.generator.team_name_prefix == "Custom"
    assert (
        balancer.generator.separated_seed_level,
        balancer.generator.maximum_seeded_players_per_team,
    ) == (2, 2)
    assert balancer.preassigned_generator.expected_player_count == 4
    assert balancer.preassigned_generator.expected_team_size == 2
    assert balancer.preassigned_generator.require_all_teams is False
    assert balancer.preassigned_generator.team_name_prefix == "Custom"
    assert balancer.preassigned_evaluator.title == "Custom evaluation"
    assert balancer.exporter.title == "Custom report"
    assert (
        composition.scoring_model.minimum_available_weight,
        composition.scoring_model.default_power,
    ) == (10, 11)
    assert composition.objective_engine.restrictions[3].max_deviation == 0.6
    assert composition.objective_engine.restrictions[4].expected_size == 2
    assert balancer.optimizer.pipeline.phases[0].max_iterations == 2
    assert balancer.stable_optimizer.config is config.stable
    restart = balancer.stable_optimizer.restart_factory
    assert (
        restart.separated_seed_level,
        restart.maximum_seeded_players_per_team,
        restart.minimum_swaps,
        restart.maximum_swaps,
        restart.partial_redistribution_ratio,
    ) == (2, 2, 1, 2, 0.25)
    result = balancer.run_players(players(), config.event.number_of_teams)
    assert len(result.teams) == 2
    assert all(len(t.players) == 2 for t in result.teams)
    assert composition.objective_engine.evaluate(result.teams).score == pytest.approx(
        result.final_score
    )


def test_compositions_have_independent_mutable_collaborators():
    config = small_config()
    a, b = create_balancing_composition(config), create_balancing_composition(config)
    assert a.scoring_model is not b.scoring_model
    assert a.objective_engine is not b.objective_engine
    for name in (
        "importer",
        "generator",
        "optimizer",
        "preassigned_generator",
        "preassigned_evaluator",
        "exporter",
        "stable_optimizer",
    ):
        assert getattr(a.balancer, name) is not getattr(b.balancer, name)
    stable_a, stable_b = a.balancer.stable_optimizer, b.balancer.stable_optimizer
    assert stable_a.restart_factory is not stable_b.restart_factory
    assert stable_a.selector is not stable_b.selector
    a.balancer.optimizer.pipeline.phases[0].enabled = False
    assert b.balancer.optimizer.pipeline.phases[0].enabled is True
    assert config.pipeline.phases[0].enabled is True


def test_balancer_helper_builds_missing_objective_from_explicit_config():
    config = small_config()
    scoring = create_scoring_model(config.scoring)
    balancer = create_balancer(config, scoring)
    objective = balancer.optimizer.evaluator.objective
    assert objective.restrictions[0].scoring_model is scoring
    assert objective.restrictions[4].expected_size == 2
    assert objective is balancer.preassigned_evaluator.objective_engine


def test_existing_restart_constructor_validation_is_preserved():
    config = small_config()
    config = replace(config, restart=replace(config.restart, minimum_swaps=0))
    with pytest.raises(ValueError, match="minimum_swaps must be greater than zero"):
        create_balancing_composition(config)


def test_global_bound_receives_custom_objective_weights_and_tolerance(monkeypatch):
    config = small_config()
    config = replace(
        config,
        objective=replace(
            config.objective,
            power_weight=43,
            elo_balance_weight=11,
            elo_spread_weight=6,
            kd_weight=23,
            team_size_weight=8,
            seed_weight=2,
        ),
        global_search=replace(config.global_search, score_tolerance=1e-5),
    )
    composition = create_balancing_composition(config)
    captured = {}
    constructor = global_factory.GlobalBoundCalculator

    def capture_bound(**kwargs):
        captured.update(kwargs)
        return constructor(**kwargs)

    monkeypatch.setattr(global_factory, "GlobalBoundCalculator", capture_bound)
    create_global_optimizer(config, composition.objective_engine)
    assert captured == {
        "power_weight": 43,
        "elo_balance_weight": 11,
        "elo_spread_weight": 6,
        "kd_weight": 23,
        "team_size_weight": 8,
        "seed_weight": 2,
        "score_tolerance": 1e-5,
    }


def test_global_construction_honors_explicit_event_and_search_budget():
    config = small_config()
    composition = create_balancing_composition(config)
    scoring = composition.scoring_model
    metrics = [
        GlobalPlayerMetrics(p, scoring.power(p), p.elo, p.kd, p.seed) for p in players()
    ]
    problem = create_global_problem(config, iter(metrics))
    assert (problem.number_of_teams, problem.team_size) == (2, 2)
    assert (problem.protected_seed_level, problem.maximum_protected_seeds_per_team) == (
        2,
        1,
    )
    assert problem.player_count == 4
    assert problem.players[0].seed == 2
    optimizer = create_global_optimizer(config, composition.objective_engine)
    other = create_global_optimizer(config, composition.objective_engine)
    assert optimizer is not other
    # Reuse the exact player instances owned by the problem for the incumbent.
    warm_start = composition.balancer.run_players([m.player for m in metrics], 2)
    result = optimizer.optimize(
        problem=problem,
        incumbent_teams=warm_start.teams,
        incumbent_score=warm_start.final_score,
    )
    assert result.stop_reason == "NODE_LIMIT"
    assert result.score == pytest.approx(warm_start.final_score)


def test_composition_import_and_construction_do_not_import_main():
    script = """
import importlib.abc
import sys
class BlockMain(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "main":
            raise AssertionError("Composition must not import main")
sys.meta_path.insert(0, BlockMain())
from configuration.application_config import ApplicationConfig
from configuration.composition_root import create_balancing_composition
from configuration.global_factory import create_global_optimizer
c = create_balancing_composition(ApplicationConfig.production_defaults())
create_global_optimizer(c.config, c.objective_engine)
assert "main" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
