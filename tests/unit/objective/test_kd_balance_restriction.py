from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.stat import Stat
from objective.restrictions.kd_balance_restriction import KdBalanceRestriction


def make_team(team_factory, team_id: int, kd: float):
    team = team_factory(team_id, [object()])
    team.statistics = MagicMock()
    team.statistics.average.side_effect = (
        lambda stat: kd if stat is Stat.KD else None
    )
    return team


def test_equal_kd_teams_score_100(team_factory):
    restriction = KdBalanceRestriction(
        weight=20.0,
        max_deviation=0.35,
    )

    result = restriction.evaluate([
        make_team(team_factory, 1, 1.00),
        make_team(team_factory, 2, 1.00),
        make_team(team_factory, 3, 1.00),
        make_team(team_factory, 4, 1.00),
    ])

    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.weight == pytest.approx(20.0)


def test_kd_score_decreases_as_dispersion_grows(team_factory):
    restriction = KdBalanceRestriction(
        weight=20.0,
        max_deviation=0.35,
    )

    balanced = restriction.evaluate([
        make_team(team_factory, 1, 0.98),
        make_team(team_factory, 2, 1.00),
        make_team(team_factory, 3, 1.01),
        make_team(team_factory, 4, 1.02),
    ])

    unbalanced = restriction.evaluate([
        make_team(team_factory, 1, 0.70),
        make_team(team_factory, 2, 0.90),
        make_team(team_factory, 3, 1.20),
        make_team(team_factory, 4, 1.40),
    ])

    assert balanced.score > unbalanced.score


def test_kd_balance_exposes_expected_name():
    assert KdBalanceRestriction().name == "KD Balance"


def test_kd_balance_rejects_invalid_max_deviation():
    with pytest.raises(ValueError):
        KdBalanceRestriction(max_deviation=0.0)

    with pytest.raises(ValueError):
        KdBalanceRestriction(max_deviation=-0.1)
