from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.stat import Stat
from objective.restrictions.elo_balance_restriction import EloBalanceRestriction


def make_team(team_factory, team_id: int, elo: float):
    team = team_factory(team_id, [object()])
    team.statistics = MagicMock()
    team.statistics.average.side_effect = lambda stat: elo if stat is Stat.ELO else None
    return team

def test_equal_elo_teams_score_matches_logistic_baseline(team_factory):
    restriction = EloBalanceRestriction(weight=10.0)
    result = restriction.evaluate([
        make_team(team_factory, 1, 1800.0),
        make_team(team_factory, 2, 1800.0),
        make_team(team_factory, 3, 1800.0),
        make_team(team_factory, 4, 1800.0),
    ])
    assert result.score == pytest.approx(95.25741268224333, abs=1e-4)
    assert result.penalty == pytest.approx(0.0)
    assert result.weight == pytest.approx(10.0)

def test_elo_balance_score_decreases_when_dispersion_grows(team_factory):
    restriction = EloBalanceRestriction(weight=10.0)
    balanced = restriction.evaluate([
        make_team(team_factory, 1, 1790.0),
        make_team(team_factory, 2, 1810.0),
        make_team(team_factory, 3, 1800.0),
        make_team(team_factory, 4, 1800.0),
    ])
    unbalanced = restriction.evaluate([
        make_team(team_factory, 1, 1500.0),
        make_team(team_factory, 2, 1700.0),
        make_team(team_factory, 3, 1900.0),
        make_team(team_factory, 4, 2100.0),
    ])
    assert balanced.score > unbalanced.score

def test_elo_balance_exposes_expected_name():
    assert EloBalanceRestriction().name == "ELO Balance"

def test_elo_balance_defaults_are_stable():
    restriction = EloBalanceRestriction()
    assert restriction.weight == pytest.approx(10.0)
    assert restriction.midpoint == pytest.approx(120.0)
    assert restriction.steepness == pytest.approx(0.025)

def test_elo_balance_rejects_non_positive_configuration():
    with pytest.raises(ValueError):
        EloBalanceRestriction(weight=0.0)
    with pytest.raises(ValueError):
        EloBalanceRestriction(midpoint=0.0)
    with pytest.raises(ValueError):
        EloBalanceRestriction(steepness=0.0)

def test_elo_balance_rejects_missing_statistics(team_factory):
    team = team_factory(1, [object()])
    team.statistics = None
    restriction = EloBalanceRestriction()
    with pytest.raises(AttributeError, match="team does not expose statistics"):
        restriction.extract_metric(team)

def test_elo_balance_rejects_negative_average_elo(team_factory):
    team = make_team(team_factory, 1, -10.0)
    restriction = EloBalanceRestriction()
    with pytest.raises(ValueError, match="Average ELO cannot be negative"):
        restriction.extract_metric(team)
