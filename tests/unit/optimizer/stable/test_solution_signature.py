from __future__ import annotations

import pytest

from models.player import Player
from models.team import Team
from optimizer.stable.solution_signature import SolutionSignature


def teams(*groups: tuple[str, ...], ids: tuple[int, ...] | None = None) -> list[Team]:
    team_ids = ids or tuple(range(1, len(groups) + 1))
    return [
        Team(team_id, [Player(name) for name in group])
        for team_id, group in zip(team_ids, groups, strict=True)
    ]


def membership(value: list[Team]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(player) for player in team.players) for team in value)


def test_signature_ignores_player_order_team_order_and_team_ids():
    first = teams(("A", "B"), ("C", "D"), ids=(1, 2))
    second = teams(("D", "C"), ("B", "A"), ids=(99, 42))

    assert SolutionSignature.from_teams(first) == SolutionSignature.from_teams(second)


def test_team_permutation_produces_equal_signature():
    original = teams(("A", "B"), ("C", "D"), ("E", "F"))

    assert SolutionSignature.from_teams(original) == SolutionSignature.from_teams(
        [original[2], original[0], original[1]]
    )


def test_different_logical_grouping_produces_different_signature():
    first = teams(("A", "B"), ("C", "D"))
    second = teams(("A", "C"), ("B", "D"))

    assert SolutionSignature.from_teams(first) != SolutionSignature.from_teams(second)


def test_signature_construction_does_not_mutate_membership_or_order():
    value = teams(("B", "A"), ("D", "C"))
    before = membership(value)

    SolutionSignature.from_teams(value)

    assert membership(value) == before


def test_fresh_players_with_same_stable_identities_produce_equal_signatures():
    first = teams(("Alpha", "Bravo"), ("Charlie", "Delta"))
    second = teams(("alpha", "BRAVO"), ("charlie", "DELTA"))

    assert all(
        left is not right
        for left, right in zip(
            (player for team in first for player in team.players),
            (player for team in second for player in team.players),
            strict=True,
        )
    )
    assert SolutionSignature.from_teams(first) == SolutionSignature.from_teams(second)


def test_duplicate_stable_player_identity_is_rejected():
    value = [Team(1, [Player("Same")]), Team(2, [Player("same")])]

    with pytest.raises(ValueError):
        SolutionSignature.from_teams(value)


def test_compact_and_stable_hash_are_deterministic_public_representations():
    first = SolutionSignature.from_teams(teams(("B", "A"), ("D", "C")))
    second = SolutionSignature.from_teams(teams(("C", "D"), ("A", "B")))

    assert first.compact == second.compact
    assert first.stable_hash == second.stable_hash
    assert (
        first.stable_hash
        == SolutionSignature.from_teams(teams(("A", "B"), ("C", "D"))).stable_hash
    )
