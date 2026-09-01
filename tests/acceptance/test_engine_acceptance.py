from __future__ import annotations

from collections.abc import Sequence

import pytest

from application.lan_balancer import LanBalancer
from application.results.optimization_result import OptimizationResult
from generators.snake_draft_generator import SnakeDraftGenerator
from importers.csstats_importer import CssStatsImporter
from main import create_objective_engine, create_pipeline, create_scoring_model
from models.player import Player
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.global_search.global_bound_calculator import GlobalBoundCalculator
from optimizer.global_search.global_optimization_config import (
    GlobalOptimizationConfig,
)
from optimizer.global_search.global_optimizer import GlobalOptimizer
from optimizer.global_search.global_player_ordering import GlobalPlayerOrdering
from optimizer.global_search.global_root_builder import GlobalRootBuilder
from optimizer.global_search.global_search_state import GlobalPlayerMetrics
from optimizer.local_optimizer import LocalOptimizer
from optimizer.modes.optimization_mode import OptimizationMode
from optimizer.modes.stable_optimization_config import StableOptimizationConfig
from optimizer.stable.deterministic_restart_generator import (
    DeterministicRestartGenerator,
)
from optimizer.stable.solution_selector import SolutionSelector
from optimizer.stable.stable_optimizer import StableOptimizer

NUMBER_OF_TEAMS = 4
TEAM_SIZE = 5
SCORE_TOLERANCE = 1e-6
STABLE_RESTART_BUDGET = 3
GLOBAL_NODE_BUDGET = 500
GLOBAL_EVALUATION_BUDGET = 50


def synthetic_players() -> list[Player]:
    """Return varied, entirely synthetic players for a four-team event."""
    elos = (
        2470, 2210, 2350, 2080, 2290,
        1930, 2160, 1850, 2020, 1760,
        1980, 1690, 1880, 1580, 1810,
        1510, 1720, 1430, 1640, 1360,
    )
    kds = (
        1.31, 1.08, 1.24, 1.15, 1.02,
        1.19, 1.11, 0.96, 1.07, 1.14,
        0.93, 1.05, 1.00, 0.89, 1.09,
        0.97, 0.86, 1.03, 0.91, 0.82,
    )
    adrs = (
        91.0, 74.0, 86.0, 80.0, 72.0,
        84.0, 77.0, 69.0, 82.0, 75.0,
        71.0, 79.0, 67.0, 73.0, 76.0,
        65.0, 70.0, 74.0, 68.0, 62.0,
    )

    return [
        Player(
            nick=f"Synthetic Player {index:02d}",
            steam_id=f"SYNTHETIC-{index:04d}",
            elo=elos[index - 1],
            level=max(1, min(10, (elos[index - 1] - 1000) // 150)),
            kd=kds[index - 1],
            adr=adrs[index - 1],
            kpr=0.53 + ((index * 7) % 24) / 100,
            winrate=43.0 + ((index * 11) % 19),
            hs=34.0 + ((index * 13) % 27),
            seed=1 if index in {1, 6, 11, 16} else None,
        )
        for index in range(1, 21)
    ]


def stable_config() -> StableOptimizationConfig:
    return StableOptimizationConfig(
        target_score=100.0,
        maximum_restarts=STABLE_RESTART_BUDGET,
        minimum_restarts=STABLE_RESTART_BUDGET,
        convergence_patience=STABLE_RESTART_BUDGET,
        score_tolerance=SCORE_TOLERANCE,
        base_seed=2026,
        target_confirmation_restarts=STABLE_RESTART_BUDGET,
        minimum_unique_solutions=0,
        maximum_total_evaluations=None,
        maximum_elapsed_seconds=None,
        stop_on_perfect_score=False,
        perfect_score=100.0,
    )


def compose_balancer(
    mode: OptimizationMode,
) -> tuple[LanBalancer, ObjectiveEngine, SnakeDraftGenerator]:
    scoring_model = create_scoring_model()
    objective_engine = create_objective_engine(scoring_model)
    generator = SnakeDraftGenerator(
        scoring_model=scoring_model,
        team_name_prefix="Acceptance Team",
        separated_seed_level=1,
        maximum_seeded_players_per_team=1,
    )
    local_optimizer = LocalOptimizer(
        evaluator=MoveEvaluator(objective=objective_engine),
        pipeline=create_pipeline(),
    )
    config = stable_config()
    stable_optimizer = StableOptimizer(
        local_optimizer=local_optimizer,
        restart_factory=DeterministicRestartGenerator(
            separated_seed_level=1,
            maximum_seeded_players_per_team=1,
            minimum_swaps=1,
            maximum_swaps=6,
            partial_redistribution_ratio=0.50,
        ),
        config=config,
        selector=SolutionSelector(config=config),
    )
    balancer = LanBalancer(
        importer=CssStatsImporter(strict=True),
        generator=generator,
        optimizer=local_optimizer,
        exporter=None,
        optimization_mode=mode,
        stable_optimizer=stable_optimizer,
    )
    return balancer, objective_engine, generator


def flattened_players(teams: Sequence[Team]) -> list[Player]:
    return [player for team in teams for player in team.players]


def canonical_membership(teams: Sequence[Team]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(
            tuple(sorted(player.steam_id for player in team.players))
            for team in teams
        )
    )


def assert_shared_invariants(
    players: Sequence[Player],
    teams: Sequence[Team],
    objective_engine: ObjectiveEngine,
):
    assert len(teams) == NUMBER_OF_TEAMS
    assert all(len(team.players) == TEAM_SIZE for team in teams)

    output_players = flattened_players(teams)
    assert len(output_players) == len(players) == NUMBER_OF_TEAMS * TEAM_SIZE
    assert {id(player) for player in output_players} == {
        id(player) for player in players
    }

    input_identities = [player.steam_id for player in players]
    output_identities = [player.steam_id for player in output_players]
    assert len(set(output_identities)) == len(output_identities)
    assert set(output_identities) == set(input_identities)
    assert all(
        sum(player.seed == 1 for player in team.players) <= 1
        for team in teams
    )

    fresh = objective_engine.evaluate(teams)
    assert fresh.penalty == pytest.approx(0.0)
    assert fresh.is_valid is True
    return fresh


def assert_application_score_consistency(
    result: OptimizationResult,
    fresh,
) -> None:
    assert result.final_score == pytest.approx(fresh.score, abs=SCORE_TOLERANCE)
    assert result.score == pytest.approx(fresh.score, abs=SCORE_TOLERANCE)
    assert result.objective_result.score == pytest.approx(
        fresh.score,
        abs=SCORE_TOLERANCE,
    )
    assert result.objective_result.penalty == pytest.approx(fresh.penalty)


def test_fast_balances_synthetic_players_through_application_flow() -> None:
    players = synthetic_players()
    balancer, objective_engine, generator = compose_balancer(OptimizationMode.FAST)
    generated = generator.generate(players, NUMBER_OF_TEAMS)
    generated_score = objective_engine.evaluate(generated).score

    result = balancer.run_players(players, NUMBER_OF_TEAMS)

    assert isinstance(result, OptimizationResult)
    fresh = assert_shared_invariants(players, result.teams, objective_engine)
    assert_application_score_consistency(result, fresh)
    assert result.final_score + SCORE_TOLERANCE >= generated_score


def test_stable_is_reproducible_through_application_flow() -> None:
    players = synthetic_players()
    balancer, objective_engine, generator = compose_balancer(OptimizationMode.STABLE)
    generated_score = objective_engine.evaluate(
        generator.generate(players, NUMBER_OF_TEAMS)
    ).score

    result = balancer.run_players(players, NUMBER_OF_TEAMS)

    assert isinstance(result, OptimizationResult)
    fresh = assert_shared_invariants(players, result.teams, objective_engine)
    assert_application_score_consistency(result, fresh)
    assert result.final_score + SCORE_TOLERANCE >= generated_score
    assert result.metadata["optimization_mode"] == OptimizationMode.STABLE.value

    replay_players = synthetic_players()
    replay_balancer, replay_objective, _ = compose_balancer(OptimizationMode.STABLE)
    replay = replay_balancer.run_players(replay_players, NUMBER_OF_TEAMS)
    replay_fresh = assert_shared_invariants(
        replay_players,
        replay.teams,
        replay_objective,
    )
    assert_application_score_consistency(replay, replay_fresh)
    assert canonical_membership(replay.teams) == canonical_membership(result.teams)
    assert replay.final_score == pytest.approx(result.final_score, abs=SCORE_TOLERANCE)


def test_global_improves_or_preserves_verified_stable_incumbent() -> None:
    players = synthetic_players()
    balancer, objective_engine, _ = compose_balancer(OptimizationMode.STABLE)
    stable_result = balancer.run_players(players, NUMBER_OF_TEAMS)
    stable_fresh = assert_shared_invariants(
        players,
        stable_result.teams,
        objective_engine,
    )
    assert_application_score_consistency(stable_result, stable_fresh)
    verified_stable_score = stable_fresh.score

    metrics = tuple(
        GlobalPlayerMetrics(
            player=player,
            power=balancer.generator.scoring_model.power(player),
            elo=float(player.elo),
            kd=float(player.kd),
            seed=player.seed,
        )
        for player in players
    )
    problem = GlobalRootBuilder(
        number_of_teams=NUMBER_OF_TEAMS,
        team_size=TEAM_SIZE,
        protected_seed_level=1,
        maximum_protected_seeds_per_team=1,
    ).build(
        players=metrics,
        ordering=GlobalPlayerOrdering(protected_seed_level=1),
    )
    config = GlobalOptimizationConfig(
        maximum_nodes=GLOBAL_NODE_BUDGET,
        maximum_evaluations=GLOBAL_EVALUATION_BUDGET,
        maximum_elapsed_seconds=None,
        score_tolerance=SCORE_TOLERANCE,
        minimum_improvement=SCORE_TOLERANCE,
        use_incumbent=True,
        use_symmetry_breaking=True,
        use_seed_pruning=True,
        use_capacity_pruning=True,
        use_power_bound=True,
        use_elo_bound=False,
        deterministic=True,
        require_proof=False,
        base_seed=2026,
    )
    optimizer = GlobalOptimizer(
        objective_engine=objective_engine,
        config=config,
        bound_calculator=GlobalBoundCalculator(
            power_weight=55.0,
            elo_balance_weight=10.0,
            elo_spread_weight=5.0,
            kd_weight=20.0,
            team_size_weight=9.0,
            seed_weight=1.0,
            score_tolerance=SCORE_TOLERANCE,
        ),
    )

    global_result = optimizer.optimize(
        problem=problem,
        incumbent_teams=stable_result.teams,
        incumbent_score=verified_stable_score,
    )

    fresh = assert_shared_invariants(players, global_result.teams, objective_engine)
    assert global_result.score == pytest.approx(fresh.score, abs=SCORE_TOLERANCE)
    assert global_result.score + SCORE_TOLERANCE >= verified_stable_score
    assert global_result.initial_incumbent_score == pytest.approx(
        verified_stable_score,
        abs=SCORE_TOLERANCE,
    )
    assert global_result.nodes_visited <= GLOBAL_NODE_BUDGET
    assert global_result.complete_solutions_evaluated <= GLOBAL_EVALUATION_BUDGET
    assert global_result.pruned_nodes == (
        global_result.capacity_prunes
        + global_result.seed_prunes
        + global_result.bound_prunes
    )
    assert global_result.stop_reason in {
        "SEARCH_EXHAUSTED",
        "NODE_LIMIT",
        "EVALUATION_LIMIT",
    }
