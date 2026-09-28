from types import SimpleNamespace

import pytest

from models.player import Player
from models.player_identity import logical_player_identity
from models.team import Team
from optimizer.global_search.global_player_ordering import GlobalPlayerOrdering
from optimizer.global_search.global_root_builder import GlobalRootBuilder
from optimizer.global_search.global_search_problem import GlobalSearchProblem
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
    GlobalTeamState,
)
from optimizer.stable.solution_signature import SolutionSignature


@pytest.mark.parametrize(
    "attributes,expected",
    [
        (
            {"identity": " CUSTOM ", "steam_id": "steam", "nickname": "nick"},
            "identity:custom",
        ),
        ({"identity": " ", "steam_id": " STEAM ", "nickname": "nick"}, "steam:steam"),
        ({"steam_id": " ", "nickname": " Straße ", "nick": "ignored"}, "nick:strasse"),
        ({"nick": " Nick "}, "nick:nick"),
        ({"identity": 0}, "identity:0"),
        ({"identity": False}, "identity:false"),
    ],
)
def test_identity_preserves_v07_priority_normalization_and_prefixes(
    attributes, expected
):
    first, second = SimpleNamespace(**attributes), SimpleNamespace(**attributes)
    assert first is not second
    assert logical_player_identity(first) == expected
    assert logical_player_identity(second) == expected
    assert SolutionSignature.player_identity(first) == expected


def test_real_player_identity_keeps_nested_v07_prefix():
    assert logical_player_identity(Player("Nick")) == "identity:nick:nick"
    assert (
        logical_player_identity(Player("Nick", steam_id="ABC")) == "identity:steam:abc"
    )


def test_anonymous_identity_preserves_all_fallback_fields_and_format():
    player = SimpleNamespace(
        elo=123.1234567890123, level=True, kd=None, rating=" HIGH "
    )
    expected = (
        "anonymous:elo=123.123456789|level=true|kd=none|rating=high|adr=none|"
        "kpr=none|dpr=none|hs=none|kast=none|winrate=none|clutch=none|matches=none|seed=none"
    )
    assert logical_player_identity(player) == expected
    assert SolutionSignature.player_identity(player) == expected


def test_present_but_empty_nickname_does_not_fall_through_to_nick():
    # getattr's default is only used when nickname is absent in v0.7.
    assert logical_player_identity(
        SimpleNamespace(nickname="", nick="ignored")
    ) == logical_player_identity(SimpleNamespace())


def test_none_is_not_a_player():
    with pytest.raises(ValueError, match="player cannot be None"):
        logical_player_identity(None)


def metrics(player):
    return GlobalPlayerMetrics(player, 10, 100, 1, None)


@pytest.mark.parametrize("entry", ["ordering", "root", "problem"])
def test_global_pool_rejects_duplicate_explicit_identity_before_search(entry):
    # The old GLOBAL key differed although SolutionSignature says same player.
    players = [
        metrics(SimpleNamespace(identity=" SAME ", steam_id="a", nickname="a")),
        metrics(SimpleNamespace(identity="same", steam_id="b", nickname="b")),
    ]
    assert players[0].identity != players[1].identity
    with pytest.raises(ValueError, match="duplicated"):
        if entry == "ordering":
            GlobalPlayerOrdering().order(players)
        elif entry == "root":
            GlobalRootBuilder(2, 1).build(players)
        else:
            GlobalSearchProblem(tuple(players), GlobalSearchState.empty(2), 2, 1)


def test_global_anonymous_player_fallback_is_stable_across_instances():
    first = metrics(SimpleNamespace(elo=10))
    second = metrics(SimpleNamespace(elo=10))
    assert first.nickname == second.nickname == logical_player_identity(first.player)
    with pytest.raises(ValueError, match="duplicated"):
        GlobalPlayerOrdering().order([first, second])


def test_global_named_ordering_key_keeps_v07_behavior():
    steam = metrics(Player("Same", steam_id="ABC"))
    nick = metrics(Player("Same"))
    assert steam.identity == ("steam", "ABC")
    assert nick.identity == ("nickname", "same")
    assert GlobalPlayerOrdering().order([steam, nick]) == (nick, steam)


def test_signature_rejects_reused_empty_team_instance():
    team = Team(1)
    with pytest.raises(ValueError, match="Duplicate Team instances"):
        SolutionSignature.from_teams([team, team])
    assert SolutionSignature.from_teams([Team(1), Team(1)]).teams == ((), ())


@pytest.mark.parametrize("same_instance", [False, True])
def test_signature_rejects_duplicate_players_by_logical_identity(same_instance):
    player = Player("Same")
    other = player if same_instance else Player("same")
    with pytest.raises(ValueError):
        SolutionSignature.from_teams([Team(1, [player]), Team(2, [other])])


def test_global_state_rejects_duplicate_player_indices_within_team():
    with pytest.raises(ValueError, match="Duplicate player indices"):
        GlobalTeamState(player_indices=(0, 0), player_count=2)


def test_global_state_rejects_duplicate_player_indices_across_teams():
    team = GlobalTeamState(player_indices=(0,), player_count=1)
    with pytest.raises(ValueError, match="Duplicate player indices"):
        GlobalSearchState((team, team), next_player_index=2, assigned_count=2)


def test_global_empty_immutable_team_state_may_be_shared():
    team = GlobalTeamState()
    assert GlobalSearchState((team, team)).assigned_count == 0


def test_valid_pool_retains_exact_player_instances():
    originals = [Player("a"), Player("b")]
    problem = GlobalRootBuilder(2, 1).build([metrics(player) for player in originals])
    assert all(
        any(item.player is player for item in problem.players) for player in originals
    )
