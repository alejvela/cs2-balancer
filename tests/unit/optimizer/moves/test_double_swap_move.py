from __future__ import annotations

import pytest

from models.player import Player
from models.team import Team
from optimizer.moves.double_swap_move import DoubleSwapMove


def player(name: str, elo: int) -> Player:
    return Player(nick=name, elo=elo)


def identity_snapshot(*teams: Team) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(member) for member in team.players) for team in teams)


def build_move() -> tuple[DoubleSwapMove, tuple[Team, ...], tuple[Player, ...]]:
    selected = tuple(player(name, 1000 * index) for index, name in enumerate("ABCD", 1))
    teammates = tuple(player(f"{name}2", 1000 * index + 100) for index, name in enumerate("ABCD", 1))
    teams = tuple(
        Team(index, [selected[index - 1], teammates[index - 1]])
        for index in range(1, 5)
    )
    move = DoubleSwapMove(
        teams[0],
        selected[0],
        teams[1],
        selected[1],
        teams[2],
        selected[2],
        teams[3],
        selected[3],
    )
    return move, teams, selected + teammates


def test_apply_and_undo_preserve_exact_double_swap_invariants():
    move, teams, players = build_move()
    player_a, player_b, player_c, player_d = players[:4]
    original = identity_snapshot(*teams)
    original_multiset = sorted(item for team in original for item in team)
    assert [team.statistics.average("elo") for team in teams] == [1050, 2050, 3050, 4050]

    move.apply()

    assert move.is_applied is True
    assert teams[0].players[0] is player_b
    assert teams[1].players[0] is player_a
    assert teams[2].players[0] is player_d
    assert teams[3].players[0] is player_c
    assert tuple(team.size for team in teams) == (2, 2, 2, 2)
    assert sorted(item for team in identity_snapshot(*teams) for item in team) == original_multiset
    assert [team.statistics.average("elo") for team in teams] == [1550, 1550, 3550, 3550]

    move.undo()

    assert move.is_applied is False
    assert identity_snapshot(*teams) == original
    assert [team.statistics.average("elo") for team in teams] == [1050, 2050, 3050, 4050]


def test_state_machine_rejects_repeated_apply_and_invalid_undo():
    move, _, _ = build_move()

    with pytest.raises(RuntimeError):
        move.undo()

    move.apply()

    with pytest.raises(RuntimeError):
        move.apply()

    move.undo()

    with pytest.raises(RuntimeError):
        move.undo()


@pytest.mark.parametrize("missing_team", ["team_a", "team_b", "team_c", "team_d"])
def test_constructor_rejects_none_teams(missing_team):
    selected = [player(name, 1000 + index) for index, name in enumerate("ABCD")]
    arguments = {
        "team_a": Team(1, [selected[0]]),
        "player_a": selected[0],
        "team_b": Team(2, [selected[1]]),
        "player_b": selected[1],
        "team_c": Team(3, [selected[2]]),
        "player_c": selected[2],
        "team_d": Team(4, [selected[3]]),
        "player_d": selected[3],
    }
    arguments[missing_team] = None

    with pytest.raises(ValueError):
        DoubleSwapMove(**arguments)


@pytest.mark.parametrize("missing_player", ["player_a", "player_b", "player_c", "player_d"])
def test_constructor_rejects_none_players(missing_player):
    selected = [player(name, 1000 + index) for index, name in enumerate("ABCD")]
    arguments = {
        "team_a": Team(1, [selected[0]]),
        "player_a": selected[0],
        "team_b": Team(2, [selected[1]]),
        "player_b": selected[1],
        "team_c": Team(3, [selected[2]]),
        "player_c": selected[2],
        "team_d": Team(4, [selected[3]]),
        "player_d": selected[3],
    }
    arguments[missing_player] = None

    with pytest.raises(ValueError):
        DoubleSwapMove(**arguments)


def test_constructor_rejects_repeated_team_identity():
    selected = [player(name, 1000 + index) for index, name in enumerate("ABCD")]
    repeated = Team(1, [selected[0], selected[1]])

    with pytest.raises(ValueError):
        DoubleSwapMove(
            repeated,
            selected[0],
            repeated,
            selected[1],
            Team(3, [selected[2]]),
            selected[2],
            Team(4, [selected[3]]),
            selected[3],
        )


def test_constructor_rejects_repeated_player_identity():
    selected = player("Same", 1500)

    with pytest.raises(ValueError):
        DoubleSwapMove(
            Team(1, [selected]),
            selected,
            Team(2, [selected]),
            selected,
            Team(3, [player("C", 3000)]),
            player("C selected", 3100),
            Team(4, [player("D", 4000)]),
            player("D selected", 4100),
        )


def test_apply_rejects_absent_selected_player_without_mutation():
    move, teams, players = build_move()
    invalid = DoubleSwapMove(
        teams[0],
        player("Absent", 500),
        teams[1],
        players[1],
        teams[2],
        players[2],
        teams[3],
        players[3],
    )
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        invalid.apply()

    assert identity_snapshot(*teams) == before


def test_apply_rejects_duplicate_source_identity_without_mutation():
    move, teams, players = build_move()
    teams[0].players.append(players[0])
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        move.apply()

    assert identity_snapshot(*teams) == before


def test_apply_rejects_incoming_player_in_destination_without_mutation():
    move, teams, players = build_move()
    teams[0].players.append(players[1])
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        move.apply()

    assert identity_snapshot(*teams) == before


def test_second_swap_failure_rolls_back_first_swap():
    move, teams, players = build_move()
    absent = player("Absent", 5000)
    invalid = DoubleSwapMove(
        teams[0],
        players[0],
        teams[1],
        players[1],
        teams[2],
        absent,
        teams[3],
        players[3],
    )
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        invalid.apply()

    assert invalid.is_applied is False
    assert identity_snapshot(*teams) == before


def test_one_player_unequal_sized_teams_work_and_keep_sizes():
    selected = [player(name, index * 1000) for index, name in enumerate("ABCD", 1)]
    teams = (
        Team(1, [selected[0]]),
        Team(2, [player("B2", 2100), selected[1]]),
        Team(3, [selected[2], player("C2", 3100), player("C3", 3200)]),
        Team(4, [player("D2", 4100), selected[3], player("D3", 4200), player("D4", 4300)]),
    )
    original = identity_snapshot(*teams)
    move = DoubleSwapMove(
        teams[0],
        selected[0],
        teams[1],
        selected[1],
        teams[2],
        selected[2],
        teams[3],
        selected[3],
    )

    move.apply()

    assert tuple(team.size for team in teams) == (1, 2, 3, 4)
    assert teams[0].players[0] is selected[1]

    move.undo()

    assert identity_snapshot(*teams) == original
