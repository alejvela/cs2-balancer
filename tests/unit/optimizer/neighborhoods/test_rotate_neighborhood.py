from __future__ import annotations

from itertools import combinations

import pytest

from models.player import Player
from models.team import Team
from optimizer.moves.rotate_move import RotateMove
from optimizer.neighborhoods.rotate_neighborhood import RotateNeighborhood


def make_teams(*sizes: int) -> tuple[Team, ...]:
    return tuple(
        Team(index, [Player(f"T{index}P{player}") for player in range(size)])
        for index, size in enumerate(sizes, 1)
    )


def snapshot(teams: tuple[Team, ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(player) for player in team.players) for team in teams)


def signature(move: RotateMove) -> tuple[int, ...]:
    return (
        id(move.team_a),
        id(move.player_a),
        id(move.team_b),
        id(move.player_b),
        id(move.team_c),
        id(move.player_c),
    )


def test_one_player_triple_has_both_directed_rotations_with_exact_references():
    teams = make_teams(1, 1, 1)
    moves = list(RotateNeighborhood().iterate(teams))

    assert all(isinstance(move, RotateMove) for move in moves)
    assert len(moves) == 2
    assert [(move.team_a, move.team_b, move.team_c) for move in moves] == [
        (teams[0], teams[1], teams[2]),
        (teams[0], teams[2], teams[1]),
    ]
    assert all(move.player_a is move.team_a.players[0] for move in moves)
    assert all(move.player_b is move.team_b.players[0] for move in moves)
    assert all(move.player_c is move.team_c.players[0] for move in moves)


def test_iterate_count_follows_two_products_per_team_triple():
    teams = make_teams(2, 3, 1, 2)
    expected = sum(
        2 * len(a.players) * len(b.players) * len(c.players)
        for a, b, c in combinations(teams, 3)
    )

    assert len(list(RotateNeighborhood().iterate(teams))) == expected


@pytest.mark.parametrize(("sizes", "expected"), [((1, 1), 0), ((1, 1, 0), 0)])
def test_iterate_requires_three_nonempty_participating_teams(sizes, expected):
    assert len(list(RotateNeighborhood().iterate(make_teams(*sizes)))) == expected


def test_iterate_does_not_mutate_membership_or_order():
    teams = make_teams(2, 2, 2)
    before = snapshot(teams)

    list(RotateNeighborhood().iterate(teams))

    assert snapshot(teams) == before


@pytest.mark.parametrize("k", [0, 1, 100])
def test_sample_is_bounded_deterministic_prefix_without_mutation(k):
    teams = make_teams(2, 1, 1)
    before = snapshot(teams)
    available = list(RotateNeighborhood().iterate(teams))

    sampled = list(RotateNeighborhood().sample(teams, k))

    assert len(sampled) <= k
    assert [signature(move) for move in sampled] == [
        signature(move) for move in available[:k]
    ]
    assert snapshot(teams) == before


def test_generated_rotation_round_trip_restores_exact_identity_and_order():
    teams = make_teams(2, 2, 2)
    before = snapshot(teams)
    move = next(RotateNeighborhood().iterate(teams))

    move.apply()
    move.undo()

    assert snapshot(teams) == before
