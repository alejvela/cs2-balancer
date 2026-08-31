from __future__ import annotations

import pytest

from models.player import Player
from models.team import Team
from optimizer.moves.rotate_move import RotateMove


def player(name: str, elo: int) -> Player:
    return Player(nick=name, elo=elo)


def identity_snapshot(*teams: Team) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(member) for member in team.players) for team in teams)


def build_move() -> tuple[RotateMove, tuple[Team, Team, Team], tuple[Player, ...]]:
    player_a = player("A", 1000)
    teammate_a = player("A2", 1100)
    player_b = player("B", 2000)
    teammate_b = player("B2", 2100)
    player_c = player("C", 3000)
    teammate_c = player("C2", 3100)
    team_a = Team(1, [player_a, teammate_a])
    team_b = Team(2, [teammate_b, player_b])
    team_c = Team(3, [player_c, teammate_c])
    move = RotateMove(team_a, player_a, team_b, player_b, team_c, player_c)
    return move, (team_a, team_b, team_c), (
        player_a,
        teammate_a,
        player_b,
        teammate_b,
        player_c,
        teammate_c,
    )


def test_apply_and_undo_preserve_exact_rotation_invariants():
    move, teams, players = build_move()
    team_a, team_b, team_c = teams
    player_a, teammate_a, player_b, teammate_b, player_c, teammate_c = players
    original = identity_snapshot(*teams)
    original_multiset = sorted(item for team in original for item in team)
    assert [team.statistics.average("elo") for team in teams] == [1050, 2050, 3050]

    move.apply()

    assert move.is_applied is True
    assert team_a.players[0] is player_c
    assert team_a.players[1] is teammate_a
    assert team_b.players[0] is teammate_b
    assert team_b.players[1] is player_a
    assert team_c.players[0] is player_b
    assert team_c.players[1] is teammate_c
    assert tuple(team.size for team in teams) == (2, 2, 2)
    assert sorted(item for team in identity_snapshot(*teams) for item in team) == original_multiset
    assert [team.statistics.average("elo") for team in teams] == [2050, 1550, 2550]

    move.undo()

    assert move.is_applied is False
    assert identity_snapshot(*teams) == original
    assert team_a.players[0] is player_a
    assert team_b.players[1] is player_b
    assert team_c.players[0] is player_c
    assert [team.statistics.average("elo") for team in teams] == [1050, 2050, 3050]


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


@pytest.mark.parametrize("missing_team", ["team_a", "team_b", "team_c"])
def test_constructor_rejects_none_teams(missing_team):
    players = [player(name, 1000 + index) for index, name in enumerate("ABC")]
    arguments = {
        "team_a": Team(1, [players[0]]),
        "player_a": players[0],
        "team_b": Team(2, [players[1]]),
        "player_b": players[1],
        "team_c": Team(3, [players[2]]),
        "player_c": players[2],
    }
    arguments[missing_team] = None

    with pytest.raises(ValueError):
        RotateMove(**arguments)


@pytest.mark.parametrize("missing_player", ["player_a", "player_b", "player_c"])
def test_constructor_rejects_none_players(missing_player):
    players = [player(name, 1000 + index) for index, name in enumerate("ABC")]
    arguments = {
        "team_a": Team(1, [players[0]]),
        "player_a": players[0],
        "team_b": Team(2, [players[1]]),
        "player_b": players[1],
        "team_c": Team(3, [players[2]]),
        "player_c": players[2],
    }
    arguments[missing_player] = None

    with pytest.raises(ValueError):
        RotateMove(**arguments)


def test_constructor_rejects_repeated_team_identity():
    players = [player(name, 1000 + index) for index, name in enumerate("ABC")]
    repeated = Team(1, [players[0], players[1]])

    with pytest.raises(ValueError):
        RotateMove(
            repeated,
            players[0],
            repeated,
            players[1],
            Team(3, [players[2]]),
            players[2],
        )


def test_constructor_rejects_repeated_player_identity():
    selected = player("Same", 1500)

    with pytest.raises(ValueError):
        RotateMove(
            Team(1, [selected]),
            selected,
            Team(2, [selected]),
            selected,
            Team(3, [player("C", 2000)]),
            player("Other", 2100),
        )


def test_apply_rejects_absent_selected_player_without_mutation():
    move, teams, players = build_move()
    team_a, team_b, team_c = teams
    _, _, player_b, _, player_c, _ = players
    absent = player("Absent", 900)
    invalid = RotateMove(team_a, absent, team_b, player_b, team_c, player_c)
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        invalid.apply()

    assert identity_snapshot(*teams) == before


def test_apply_rejects_duplicate_source_identity_without_mutation():
    move, teams, players = build_move()
    team_a, team_b, team_c = teams
    player_a, _, player_b, _, player_c, _ = players
    team_a.players.append(player_a)
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        move.apply()

    assert identity_snapshot(*teams) == before


def test_apply_rejects_incoming_player_in_destination_without_mutation():
    move, teams, players = build_move()
    team_a, _, _ = teams
    _, _, _, _, player_c, _ = players
    team_a.players.append(player_c)
    before = identity_snapshot(*teams)

    with pytest.raises(ValueError):
        move.apply()

    assert identity_snapshot(*teams) == before


def test_one_player_unequal_sized_teams_work_and_keep_sizes():
    player_a = player("A", 1000)
    player_b = player("B", 2000)
    player_c = player("C", 3000)
    team_a = Team(1, [player_a])
    team_b = Team(2, [player("B2", 2100), player_b])
    team_c = Team(3, [player_c, player("C2", 3100), player("C3", 3200)])
    original = identity_snapshot(team_a, team_b, team_c)
    move = RotateMove(team_a, player_a, team_b, player_b, team_c, player_c)

    move.apply()

    assert (team_a.size, team_b.size, team_c.size) == (1, 2, 3)
    assert team_a.players[0] is player_c

    move.undo()

    assert identity_snapshot(team_a, team_b, team_c) == original

