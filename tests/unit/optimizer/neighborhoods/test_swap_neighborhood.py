from __future__ import annotations

from itertools import combinations

import pytest

from models.player import Player
from models.team import Team
from optimizer.moves.swap_move import SwapMove
from optimizer.neighborhoods.swap_neighborhood import SwapNeighborhood


def make_teams(*sizes: int) -> tuple[Team, ...]:
    return tuple(
        Team(index, [Player(f"T{index}P{player}") for player in range(size)])
        for index, size in enumerate(sizes, 1)
    )


def snapshot(teams: tuple[Team, ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(player) for player in team.players) for team in teams)


def signature(move: SwapMove) -> tuple[int, int, int, int]:
    return (id(move.team_a), id(move.player_a), id(move.team_b), id(move.player_b))


def test_iterate_builds_canonical_swap_moves_with_exact_references():
    teams = make_teams(2, 3, 1)
    moves = list(SwapNeighborhood().iterate(teams))

    assert all(isinstance(move, SwapMove) for move in moves)
    assert len(moves) == sum(
        len(a.players) * len(b.players) for a, b in combinations(teams, 2)
    )
    assert {(id(move.team_a), id(move.team_b)) for move in moves} == {
        (id(team_a), id(team_b)) for team_a, team_b in combinations(teams, 2)
    }
    assert all(
        any(move.player_a is player for player in move.team_a.players) for move in moves
    )
    assert all(
        any(move.player_b is player for player in move.team_b.players) for move in moves
    )


@pytest.mark.parametrize(
    ("sizes", "expected"),
    [((1, 1), 1), ((1,), 0), ((), 0), ((2, 0, 3), 6), ((2, 3), 6)],
)
def test_iterate_count_handles_small_empty_and_unequal_teams(sizes, expected):
    assert len(list(SwapNeighborhood().iterate(make_teams(*sizes)))) == expected


def test_iterate_does_not_mutate_membership_or_order():
    teams = make_teams(2, 3, 1)
    before = snapshot(teams)

    list(SwapNeighborhood().iterate(teams))

    assert snapshot(teams) == before


@pytest.mark.parametrize("k", [0, 1, 100])
def test_sample_is_bounded_deterministic_prefix_without_mutation(k):
    teams = make_teams(2, 2, 1)
    before = snapshot(teams)
    available = list(SwapNeighborhood().iterate(teams))

    sampled = list(SwapNeighborhood().sample(teams, k))

    assert len(sampled) <= k
    assert [signature(move) for move in sampled] == [
        signature(move) for move in available[:k]
    ]
    assert snapshot(teams) == before


def test_generated_swap_round_trip_restores_exact_identity_and_order():
    teams = make_teams(2, 2)
    before = snapshot(teams)
    move = next(SwapNeighborhood().iterate(teams))

    move.apply()
    move.undo()

    assert snapshot(teams) == before
