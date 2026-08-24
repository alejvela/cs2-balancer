from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.stat import Stat
from objective.restrictions.elo_spread_restriction import EloSpreadRestriction


def make_team(team_factory, team_id: int, elo: float):
    team = team_factory(team_id, [object()])
    team.statistics = MagicMock()
    team.statistics.average.side_effect = lambda stat: elo if stat is Stat.ELO else None
    return team

def test_spread_inside_ideal_scores_100(team_factory):
    restriction = EloSpreadRestriction()
    result = restriction.evaluate([
        make_team(team_factory, 1, 1500.0),
        make_team(team_factory, 2, 1580.0),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.details["elo_spread"] == pytest.approx(80.0)
    assert result.details["within_ideal_spread"] is True
    assert result.details["spread_category"] == "excellent"

def test_spread_at_maximum_scores_zero(team_factory):
    restriction = EloSpreadRestriction()
    result = restriction.evaluate([
        make_team(team_factory, 1, 1500.0),
        make_team(team_factory, 2, 1900.0),
    ])
    assert result.score == pytest.approx(0.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.details["elo_spread"] == pytest.approx(400.0)
    assert result.details["spread_category"] == "extreme"

def test_spread_between_good_and_acceptable_is_interpolated(team_factory):
    restriction = EloSpreadRestriction()
    result = restriction.evaluate([
        make_team(team_factory, 1, 1500.0),
        make_team(team_factory, 2, 1675.0),
    ])
    assert result.score == pytest.approx(72.5)
    assert result.penalty == pytest.approx(0.0)
    assert result.details["elo_spread"] == pytest.approx(175.0)
    assert result.details["spread_category"] == "acceptable"

@pytest.mark.parametrize(("spread", "expected_score"), [
    (100.0, 100.0),
    (150.0, 85.0),
    (200.0, 60.0),
    (300.0, 25.0),
    (400.0, 0.0),
])
def test_default_threshold_scores(spread, expected_score):
    restriction = EloSpreadRestriction()
    assert restriction._score_spread(spread) == pytest.approx(expected_score)

def test_spread_rejects_non_ascending_thresholds():
    with pytest.raises(ValueError, match="ascending order"):
        EloSpreadRestriction(
            ideal_spread=100.0,
            good_spread=90.0,
            acceptable_spread=200.0,
            poor_spread=300.0,
            maximum_spread=400.0,
        )

def test_spread_rejects_duplicate_thresholds():
    with pytest.raises(ValueError, match="must be unique"):
        EloSpreadRestriction(
            ideal_spread=100.0,
            good_spread=150.0,
            acceptable_spread=150.0,
            poor_spread=300.0,
            maximum_spread=400.0,
        )

def test_spread_requires_two_teams(team_factory):
    restriction = EloSpreadRestriction()
    with pytest.raises(ValueError, match="at least two teams"):
        restriction.evaluate([make_team(team_factory, 1, 1800.0)])

def test_spread_rejects_negative_average_elo(team_factory):
    restriction = EloSpreadRestriction()
    with pytest.raises(ValueError, match="Average ELO cannot be negative"):
        restriction.evaluate([
            make_team(team_factory, 1, -1.0),
            make_team(team_factory, 2, 1800.0),
        ])
