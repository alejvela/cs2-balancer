from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from objective.restrictions.power_balance_restriction import PowerBalanceRestriction
from scoring.scoring_model import ScoringModel


@pytest.mark.parametrize(
    ("spread", "global_average", "expected"),
    [
        (0.0, 50.0, 100.0),
        (5.0, 50.0, 90.0),
        (10.0, 50.0, 80.0),
        (25.0, 50.0, 50.0),
        (50.0, 50.0, 0.0),
        (75.0, 50.0, 0.0),
        (0.0, 0.0, 100.0),
        (1.0, 0.0, 0.0),
    ],
)
def test_calculate_score(spread, global_average, expected):
    assert PowerBalanceRestriction._calculate_score(
        spread=spread,
        global_average=global_average,
    ) == pytest.approx(expected)


def test_equal_team_power_scores_100(team_factory):
    players = [object(), object(), object(), object()]
    powers = {
        id(players[0]): 40.0,
        id(players[1]): 60.0,
        id(players[2]): 45.0,
        id(players[3]): 55.0,
    }

    scoring_model = MagicMock(spec=ScoringModel)
    scoring_model.power.side_effect = lambda player: powers[id(player)]

    restriction = PowerBalanceRestriction(
        scoring_model=scoring_model,
        weight=55.0,
    )

    result = restriction.evaluate([
        team_factory(1, players[:2]),
        team_factory(2, players[2:]),
    ])

    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.weight == pytest.approx(55.0)


def test_score_decreases_as_power_spread_increases(team_factory):
    balanced = [object(), object(), object(), object()]
    unbalanced = [object(), object(), object(), object()]

    powers = {
        id(balanced[0]): 50.0,
        id(balanced[1]): 50.0,
        id(balanced[2]): 50.0,
        id(balanced[3]): 50.0,
        id(unbalanced[0]): 70.0,
        id(unbalanced[1]): 70.0,
        id(unbalanced[2]): 30.0,
        id(unbalanced[3]): 30.0,
    }

    scoring_model = MagicMock(spec=ScoringModel)
    scoring_model.power.side_effect = lambda player: powers[id(player)]

    restriction = PowerBalanceRestriction(
        scoring_model=scoring_model,
        weight=55.0,
    )

    balanced_result = restriction.evaluate([
        team_factory(1, balanced[:2]),
        team_factory(2, balanced[2:]),
    ])

    unbalanced_result = restriction.evaluate([
        team_factory(1, unbalanced[:2]),
        team_factory(2, unbalanced[2:]),
    ])

    assert balanced_result.score == pytest.approx(100.0)
    assert unbalanced_result.score < balanced_result.score


def test_requires_at_least_two_teams(team_factory):
    scoring_model = MagicMock(spec=ScoringModel)
    restriction = PowerBalanceRestriction(scoring_model=scoring_model)

    with pytest.raises(ValueError, match="at least two teams"):
        restriction.evaluate([team_factory(1)])


def test_rejects_empty_team(team_factory):
    scoring_model = MagicMock(spec=ScoringModel)
    restriction = PowerBalanceRestriction(scoring_model=scoring_model)

    with pytest.raises(ValueError, match="cannot be empty"):
        restriction.evaluate([
            team_factory(1, []),
            team_factory(2, [object()]),
        ])
