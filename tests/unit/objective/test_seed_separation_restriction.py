from __future__ import annotations

from types import SimpleNamespace

import pytest

from objective.restrictions.seed_separation_restriction import SeedSeparationRestriction


def player(seed=None, nickname="Player"):
    return SimpleNamespace(seed=seed, nickname=nickname)

def test_one_seed_per_team_is_valid(team_factory):
    restriction = SeedSeparationRestriction(
        seed_level=1, maximum_per_team=1,
        penalty_per_excess_player=100.0,
        maximum_penalty=100.0, weight=1.0,
    )
    result = restriction.evaluate([
        team_factory(1, [player(1,"a"), player(), player()]),
        team_factory(2, [player(1,"b"), player(), player()]),
        team_factory(3, [player(1,"c"), player(), player()]),
        team_factory(4, [player(1,"d"), player(), player()]),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.details["valid"] is True
    assert result.details["total_excess"] == 0

def test_two_seed_ones_in_same_team_are_penalized(team_factory):
    restriction = SeedSeparationRestriction(
        seed_level=1, maximum_per_team=1,
        penalty_per_excess_player=100.0,
        maximum_penalty=100.0, weight=1.0,
    )
    result = restriction.evaluate([
        team_factory(1, [player(1,"a"), player(1,"b"), player()]),
        team_factory(2, [player(), player(), player()]),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(100.0)
    assert result.details["valid"] is False
    assert result.details["total_excess"] == 1
    assert result.details["violation_count"] == 1

def test_other_seed_levels_do_not_count(team_factory):
    restriction = SeedSeparationRestriction()
    result = restriction.evaluate([
        team_factory(1, [player(1), player(2), player(2)]),
        team_factory(2, [player(1), player(3), player()]),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.details["valid"] is True

def test_seed_penalty_is_capped(team_factory):
    restriction = SeedSeparationRestriction()
    result = restriction.evaluate([
        team_factory(1, [player(1, f"a{i}") for i in range(5)]),
        team_factory(2, [player(1, f"b{i}") for i in range(5)]),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(100.0)
    assert result.details["total_excess"] == 8

def test_seed_restriction_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        SeedSeparationRestriction(seed_level=0)
    with pytest.raises(ValueError):
        SeedSeparationRestriction(maximum_per_team=-1)
    with pytest.raises(ValueError):
        SeedSeparationRestriction(penalty_per_excess_player=0.0)
