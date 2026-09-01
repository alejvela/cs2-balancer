from __future__ import annotations

import pytest

from models.player import Player
from optimizer.global_search.global_root_builder import GlobalRootBuilder
from optimizer.global_search.global_search_state import GlobalPlayerMetrics


def metrics(
    name: str,
    power: float,
    *,
    seed: int | None = None,
    steam_id: str | None = None,
) -> GlobalPlayerMetrics:
    player = Player(name, steam_id=steam_id)
    return GlobalPlayerMetrics(player, power=power, elo=power * 10, kd=1, seed=seed)


def test_builder_requires_exact_player_count():
    builder = GlobalRootBuilder(number_of_teams=2, team_size=2)

    with pytest.raises(ValueError):
        builder.build([metrics("A", 10), metrics("B", 20), metrics("C", 30)])


def test_builder_rejects_duplicate_logical_identity():
    players = [
        metrics("Same", 10),
        metrics("same", 20),
        metrics("C", 30),
        metrics("D", 40),
    ]

    with pytest.raises(ValueError):
        GlobalRootBuilder(2, 2).build(players)


def test_builder_orders_players_deterministically_for_same_input():
    players = [
        metrics("A", 10),
        metrics("B", 40),
        metrics("C", 20),
        metrics("D", 30),
    ]
    builder = GlobalRootBuilder(2, 2, protected_seed_level=None)

    first = builder.build(players)
    second = builder.build(players)

    assert tuple(player.identity for player in first.players) == tuple(
        player.identity for player in second.players
    )


def test_protected_seeds_are_preassigned_canonically_and_first_in_order():
    seed_b = metrics("Seed B", 20, seed=1)
    normal = metrics("Normal", 40)
    seed_a = metrics("Seed A", 30, seed=1)
    other = metrics("Other", 10)

    problem = GlobalRootBuilder(2, 2).build([seed_b, normal, seed_a, other])

    assert problem.preassigned_player_count == 2
    assert all(player.seed == 1 for player in problem.players[:2])
    assert problem.root_state.team_sizes == (1, 1)
    assert problem.root_state.protected_seed_counts == (1, 1)
    assert problem.root_state.teams[0].player_indices == (0,)
    assert problem.root_state.teams[1].player_indices == (1,)


def test_impossible_protected_seed_capacity_is_rejected():
    players = [metrics(f"S{i}", i + 1, seed=1) for i in range(3)]
    players.append(metrics("Normal", 10))

    with pytest.raises(ValueError):
        GlobalRootBuilder(2, 2, maximum_protected_seeds_per_team=1).build(players)


def test_problem_retains_exact_original_player_references():
    values = [metrics(name, index) for index, name in enumerate("ABCD", 1)]
    originals = {id(value.player) for value in values}

    problem = GlobalRootBuilder(2, 2, protected_seed_level=None).build(values)

    assert {id(value.player) for value in problem.players} == originals
