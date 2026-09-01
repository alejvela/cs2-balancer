"""Frozen LAN 2026 regression contract.

For an intentional engine change, inspect power, objective-component, and
canonical-team differences; verify structural validity and product impact;
then explicitly regenerate and manually review the candidate baseline. Update
it in the same PR with an explanation. Never auto-accept or weaken a snapshot
merely to make CI pass.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from generators.snake_draft_generator import SnakeDraftGenerator
from main import create_objective_engine, create_pipeline, create_scoring_model
from models.player import Player
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.local_optimizer import LocalOptimizer
from optimizer.modes.stable_optimization_config import StableOptimizationConfig
from optimizer.stable.deterministic_restart_generator import (
    DeterministicRestartGenerator,
)
from optimizer.stable.solution_selector import SolutionSelector
from optimizer.stable.stable_optimizer import StableOptimizer
from tests.regression.helpers import (
    canonical_team_membership,
    load_lan_2026_baseline,
    load_lan_2026_fixture,
    load_lan_2026_players,
)

NUMBER_OF_TEAMS = 4
TEAM_SIZE = 5
SCORE_TOLERANCE = 1e-6
COMPONENT_NAMES = (
    "Power Balance",
    "ELO Balance",
    "ELO Spread",
    "KD Balance",
    "Team Size",
    "Seed 1 Separation",
)


def regression_stable_config() -> StableOptimizationConfig:
    return StableOptimizationConfig(
        target_score=100.0,
        maximum_restarts=6,
        minimum_restarts=6,
        convergence_patience=6,
        score_tolerance=SCORE_TOLERANCE,
        base_seed=2026,
        target_confirmation_restarts=6,
        minimum_unique_solutions=0,
        maximum_total_evaluations=None,
        maximum_elapsed_seconds=None,
        stop_on_perfect_score=False,
        perfect_score=100.0,
    )


def compose_engine():
    scoring_model = create_scoring_model()
    objective_engine = create_objective_engine(scoring_model)
    generator = SnakeDraftGenerator(
        scoring_model=scoring_model,
        team_name_prefix="LAN 2026 Team",
        separated_seed_level=1,
        maximum_seeded_players_per_team=1,
    )
    local_optimizer = LocalOptimizer(
        evaluator=MoveEvaluator(objective=objective_engine),
        pipeline=create_pipeline(),
    )
    config = regression_stable_config()
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
    return scoring_model, objective_engine, generator, stable_optimizer


def assert_structural_invariants(
    players: Sequence[Player],
    teams: Sequence[Team],
    objective_engine: ObjectiveEngine,
):
    assert len(teams) == NUMBER_OF_TEAMS
    assert all(len(team.players) == TEAM_SIZE for team in teams)

    output_players = [player for team in teams for player in team.players]
    assert len(output_players) == len(players) == NUMBER_OF_TEAMS * TEAM_SIZE
    assert {id(player) for player in output_players} == {
        id(player) for player in players
    }
    assert {player.steam_id for player in output_players} == {
        player.steam_id for player in players
    }
    assert len({player.steam_id for player in output_players}) == len(players)
    assert all(
        sum(player.seed == 1 for player in team.players) <= 1
        for team in teams
    )

    fresh = objective_engine.evaluate(teams)
    assert fresh.penalty == pytest.approx(0.0, abs=SCORE_TOLERANCE)
    assert fresh.is_valid is True
    return fresh


def test_fixture_integrity_and_fresh_loading() -> None:
    fixture = load_lan_2026_fixture()
    first = load_lan_2026_players()
    second = load_lan_2026_players()

    assert fixture["fixture_version"] == 1
    assert fixture["event"] == "LAN 2026"
    assert fixture["snapshot_date"] is None
    assert fixture["snapshot_date_status"] == "unverified"
    assert fixture["source"] == "FACEIT Data API snapshot"
    assert "19 CS2 records and one CS:GO fallback" in fixture["provenance_note"]
    assert len(first) == len(second) == 20
    assert all(left is not right for left, right in zip(first, second, strict=True))
    assert len({player.nick.casefold() for player in first}) == 20
    assert len({player.steam_id for player in first}) == 20
    assert sum(player.seed == 1 for player in first) == 4
    assert all(player.team_number is None for player in first)
    assert next(player for player in first if player.nick == "robertw0w").adr is None
    assert {player.steam_id for player in first} == {
        player.steam_id for player in second
    }


def test_scoring_and_initial_generation_match_frozen_fingerprint() -> None:
    baseline = load_lan_2026_baseline()
    players = load_lan_2026_players()
    scoring_model, objective_engine, generator, _ = compose_engine()

    assert set(baseline["player_powers"]) == {
        player.steam_id for player in players
    }
    for player in players:
        assert scoring_model.power(player) == pytest.approx(
            baseline["player_powers"][player.steam_id],
            abs=SCORE_TOLERANCE,
        )

    initial_teams = generator.generate(players, NUMBER_OF_TEAMS)
    fresh = assert_structural_invariants(players, initial_teams, objective_engine)
    assert canonical_team_membership(initial_teams) == tuple(
        tuple(team) for team in baseline["initial"]["canonical_teams"]
    )
    assert fresh.score == pytest.approx(
        baseline["initial"]["score"],
        abs=SCORE_TOLERANCE,
    )


def test_stable_result_matches_frozen_fingerprint() -> None:
    baseline = load_lan_2026_baseline()
    players = load_lan_2026_players()
    _, objective_engine, generator, stable_optimizer = compose_engine()
    initial_teams = generator.generate(players, NUMBER_OF_TEAMS)

    assert baseline["package_version"] == "0.5.0"
    assert baseline["mode"] == "STABLE"
    assert baseline["score_tolerance"] == SCORE_TOLERANCE
    assert baseline["stable_config"] == regression_stable_config().as_dict()

    result = stable_optimizer.optimize(initial_teams)

    fresh = assert_structural_invariants(players, result.teams, objective_engine)
    assert result.final_score == pytest.approx(fresh.score, abs=SCORE_TOLERANCE)
    assert canonical_team_membership(result.teams) == tuple(
        tuple(team) for team in baseline["stable"]["canonical_teams"]
    )
    assert fresh.score == pytest.approx(
        baseline["stable"]["score"],
        abs=SCORE_TOLERANCE,
    )
    assert fresh.penalty == pytest.approx(
        baseline["stable"]["penalty"],
        abs=SCORE_TOLERANCE,
    )
    assert set(baseline["stable"]["components"]) == set(COMPONENT_NAMES)
    for component_name in COMPONENT_NAMES:
        assert fresh[component_name].score == pytest.approx(
            baseline["stable"]["components"][component_name],
            abs=SCORE_TOLERANCE,
        )
