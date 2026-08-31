from __future__ import annotations

from itertools import combinations

import pytest

from models.player import Player
from models.team import Team
from optimizer.moves.double_swap_move import DoubleSwapMove
from optimizer.neighborhoods.double_swap_neighborhood import DoubleSwapNeighborhood


def make_teams(*sizes: int) -> tuple[Team, ...]:
    return tuple(
        Team(index, [Player(f"T{index}P{player}") for player in range(size)])
        for index, size in enumerate(sizes, 1)
    )


def snapshot(teams: tuple[Team, ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(player) for player in team.players) for team in teams)


def pairing(move: DoubleSwapMove) -> frozenset[frozenset[int]]:
    return frozenset(
        (
            frozenset((id(move.team_a), id(move.team_b))),
            frozenset((id(move.team_c), id(move.team_d))),
        )
    )


def signature(move: DoubleSwapMove) -> tuple[int, ...]:
    return (
        id(move.team_a),
        id(move.player_a),
        id(move.team_b),
        id(move.player_b),
        id(move.team_c),
        id(move.player_c),
        id(move.team_d),
        id(move.player_d),
    )


def test_four_one_player_teams_have_exactly_three_canonical_pairings():
    teams = make_teams(1, 1, 1, 1)
    moves = list(DoubleSwapNeighborhood().iterate(teams))
    expected = {
        frozenset(
            (
                frozenset((id(teams[0]), id(teams[1]))),
                frozenset((id(teams[2]), id(teams[3]))),
            )
        ),
        frozenset(
            (
                frozenset((id(teams[0]), id(teams[2]))),
                frozenset((id(teams[1]), id(teams[3]))),
            )
        ),
        frozenset(
            (
                frozenset((id(teams[0]), id(teams[3]))),
                frozenset((id(teams[1]), id(teams[2]))),
            )
        ),
    }

    assert all(isinstance(move, DoubleSwapMove) for move in moves)
    assert len(moves) == 3
    assert {pairing(move) for move in moves} == expected
    assert len({pairing(move) for move in moves}) == len(moves)


def test_iterate_count_follows_three_products_per_team_quadruple():
    teams = make_teams(2, 1, 2, 1, 1)
    expected = sum(
        3 * len(a.players) * len(b.players) * len(c.players) * len(d.players)
        for a, b, c, d in combinations(teams, 4)
    )

    assert len(list(DoubleSwapNeighborhood().iterate(teams))) == expected


@pytest.mark.parametrize(("sizes", "expected"), [((1, 1, 1), 0), ((1, 1, 1, 0), 0)])
def test_iterate_requires_four_nonempty_participating_teams(sizes, expected):
    assert len(list(DoubleSwapNeighborhood().iterate(make_teams(*sizes)))) == expected


def test_generated_moves_capture_exact_team_and_player_references():
    teams = make_teams(1, 1, 1, 1)

    for move in DoubleSwapNeighborhood().iterate(teams):
        assert all(
            any(player is candidate for candidate in team.players)
            for team, player in (
                (move.team_a, move.player_a),
                (move.team_b, move.player_b),
                (move.team_c, move.player_c),
                (move.team_d, move.player_d),
            )
        )


def test_iterate_does_not_mutate_membership_or_order():
    teams = make_teams(2, 1, 2, 1)
    before = snapshot(teams)

    list(DoubleSwapNeighborhood().iterate(teams))

    assert snapshot(teams) == before


@pytest.mark.parametrize("k", [0, 1, 100])
def test_sample_is_bounded_deterministic_prefix_without_mutation(k):
    teams = make_teams(1, 1, 1, 1)
    before = snapshot(teams)
    available = list(DoubleSwapNeighborhood().iterate(teams))

    sampled = list(DoubleSwapNeighborhood().sample(teams, k))

    assert len(sampled) <= k
    assert [signature(move) for move in sampled] == [
        signature(move) for move in available[:k]
    ]
    assert snapshot(teams) == before


def test_generated_double_swap_round_trip_restores_exact_identity_and_order():
    teams = make_teams(2, 2, 2, 2)
    before = snapshot(teams)
    move = next(DoubleSwapNeighborhood().iterate(teams))

    move.apply()
    move.undo()

    assert snapshot(teams) == before
