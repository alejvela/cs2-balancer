from __future__ import annotations

import pytest

from models.player import Player
from models.team import Team
from optimizer.moves.swap_move import SwapMove


def player(name: str, elo: int) -> Player:
    return Player(nick=name, elo=elo)


def identity_snapshot(*teams: Team) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(member) for member in team.players) for team in teams)


def test_apply_and_undo_preserve_exact_swap_invariants():
    player_a = player("A", 1000)
    teammate_a = player("A2", 1200)
    player_b = player("B", 2000)
    teammate_b = player("B2", 2200)
    team_a = Team(1, [player_a, teammate_a])
    team_b = Team(2, [teammate_b, player_b])
    original = identity_snapshot(team_a, team_b)
    original_sizes = (team_a.size, team_b.size)
    original_identity_multiset = sorted(original[0] + original[1])
    assert team_a.statistics.average("elo") == pytest.approx(1100.0)
    assert team_b.statistics.average("elo") == pytest.approx(2100.0)
    move = SwapMove(team_a, player_a, team_b, player_b)

    move.apply()

    assert move.is_applied is True
    assert team_a.players[0] is player_b
    assert team_a.players[1] is teammate_a
    assert team_b.players[0] is teammate_b
    assert team_b.players[1] is player_a
    assert (team_a.size, team_b.size) == original_sizes
    assert sorted(identity_snapshot(team_a, team_b)[0] + identity_snapshot(team_a, team_b)[1]) == original_identity_multiset
    assert team_a.statistics.average("elo") == pytest.approx(1600.0)
    assert team_b.statistics.average("elo") == pytest.approx(1600.0)

    move.undo()

    assert move.is_applied is False
    assert identity_snapshot(team_a, team_b) == original
    assert team_a.players[0] is player_a
    assert team_a.players[1] is teammate_a
    assert team_b.players[0] is teammate_b
    assert team_b.players[1] is player_b
    assert (team_a.size, team_b.size) == original_sizes
    assert team_a.statistics.average("elo") == pytest.approx(1100.0)
    assert team_b.statistics.average("elo") == pytest.approx(2100.0)


def test_move_mutates_captured_teams_not_optional_argument():
    player_a = player("A", 1000)
    player_b = player("B", 2000)
    team_a = Team(1, [player_a])
    team_b = Team(2, [player_b])
    unrelated = Team(3, [player("Other", 1500)])
    unrelated_before = identity_snapshot(unrelated)

    SwapMove(team_a, player_a, team_b, player_b).apply([unrelated])

    assert team_a.players[0] is player_b
    assert team_b.players[0] is player_a
    assert identity_snapshot(unrelated) == unrelated_before


def test_state_machine_rejects_repeated_apply_and_invalid_undo():
    player_a = player("A", 1000)
    player_b = player("B", 2000)
    move = SwapMove(Team(1, [player_a]), player_a, Team(2, [player_b]), player_b)

    with pytest.raises(RuntimeError):
        move.undo()

    move.apply()

    with pytest.raises(RuntimeError):
        move.apply()

    move.undo()

    with pytest.raises(RuntimeError):
        move.undo()


@pytest.mark.parametrize("missing_team", ["team_a", "team_b"])
def test_constructor_rejects_none_teams(missing_team):
    player_a = player("A", 1000)
    player_b = player("B", 2000)
    arguments = {
        "team_a": Team(1, [player_a]),
        "player_a": player_a,
        "team_b": Team(2, [player_b]),
        "player_b": player_b,
    }
    arguments[missing_team] = None

    with pytest.raises(ValueError):
        SwapMove(**arguments)


@pytest.mark.parametrize("missing_player", ["player_a", "player_b"])
def test_constructor_rejects_none_players(missing_player):
    player_a = player("A", 1000)
    player_b = player("B", 2000)
    arguments = {
        "team_a": Team(1, [player_a]),
        "player_a": player_a,
        "team_b": Team(2, [player_b]),
        "player_b": player_b,
    }
    arguments[missing_player] = None

    with pytest.raises(ValueError):
        SwapMove(**arguments)


def test_constructor_rejects_repeated_team_identity():
    player_a = player("A", 1000)
    player_b = player("B", 2000)
    team = Team(1, [player_a, player_b])

    with pytest.raises(ValueError):
        SwapMove(team, player_a, team, player_b)


def test_constructor_rejects_repeated_player_identity():
    selected = player("Same", 1500)

    with pytest.raises(ValueError):
        SwapMove(Team(1, [selected]), selected, Team(2, [selected]), selected)


def test_apply_rejects_player_absent_from_source_without_mutation():
    selected_a = player("A", 1000)
    actual_a = player("Actual", 1100)
    selected_b = player("B", 2000)
    team_a = Team(1, [actual_a])
    team_b = Team(2, [selected_b])
    before = identity_snapshot(team_a, team_b)

    with pytest.raises(ValueError):
        SwapMove(team_a, selected_a, team_b, selected_b).apply()

    assert identity_snapshot(team_a, team_b) == before


def test_apply_rejects_duplicate_source_identity_without_mutation():
    selected_a = player("A", 1000)
    selected_b = player("B", 2000)
    team_a = Team(1, [selected_a, selected_a])
    team_b = Team(2, [selected_b])
    before = identity_snapshot(team_a, team_b)

    with pytest.raises(ValueError):
        SwapMove(team_a, selected_a, team_b, selected_b).apply()

    assert identity_snapshot(team_a, team_b) == before


def test_apply_rejects_incoming_player_in_destination_without_mutation():
    selected_a = player("A", 1000)
    selected_b = player("B", 2000)
    team_a = Team(1, [selected_a, selected_b])
    team_b = Team(2, [selected_b])
    before = identity_snapshot(team_a, team_b)

    with pytest.raises(ValueError):
        SwapMove(team_a, selected_a, team_b, selected_b).apply()

    assert identity_snapshot(team_a, team_b) == before


def test_one_player_unequal_sized_teams_work_and_keep_sizes():
    selected_a = player("A", 1000)
    selected_b = player("B", 2000)
    team_a = Team(1, [selected_a])
    team_b = Team(2, [player("B2", 2100), selected_b, player("B3", 2200)])
    original = identity_snapshot(team_a, team_b)
    move = SwapMove(team_a, selected_a, team_b, selected_b)

    move.apply()

    assert (team_a.size, team_b.size) == (1, 3)
    assert team_a.players[0] is selected_b

    move.undo()

    assert identity_snapshot(team_a, team_b) == original

