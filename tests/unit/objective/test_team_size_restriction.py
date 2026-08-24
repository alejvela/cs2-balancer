from __future__ import annotations

import pytest

from objective.restrictions.team_size_restriction import TeamSizeRestriction


def test_all_teams_with_expected_size_score_100(team_factory):
    restriction = TeamSizeRestriction(expected_size=5, weight=9.0)
    result = restriction.evaluate([
        team_factory(1, [object() for _ in range(5)]),
        team_factory(2, [object() for _ in range(5)]),
        team_factory(3, [object() for _ in range(5)]),
        team_factory(4, [object() for _ in range(5)]),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.weight == pytest.approx(9.0)
    assert result.details["valid"] is True
    assert result.details["compliance_score"] == pytest.approx(100.0)

def test_wrong_team_size_is_structurally_invalid(team_factory):
    restriction = TeamSizeRestriction(expected_size=5, weight=9.0)
    result = restriction.evaluate([
        team_factory(1, [object() for _ in range(4)]),
        team_factory(2, [object() for _ in range(6)]),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(50.0)
    assert result.details["valid"] is False
    assert result.details["invalid_team_count"] == 2
    assert result.details["total_absolute_difference"] == 2
    assert result.details["compliance_score"] == pytest.approx(80.0)

def test_team_size_penalty_is_capped_at_100(team_factory):
    restriction = TeamSizeRestriction(expected_size=5, penalty_per_position=25.0)
    result = restriction.evaluate([
        team_factory(1, []),
        team_factory(2, []),
    ])
    assert result.score == pytest.approx(100.0)
    assert result.penalty == pytest.approx(100.0)
    assert result.details["total_absolute_difference"] == 10

def test_team_size_rejects_invalid_expected_size():
    with pytest.raises(ValueError):
        TeamSizeRestriction(expected_size=0)
    with pytest.raises(ValueError):
        TeamSizeRestriction(expected_size=-1)

def test_team_size_rejects_invalid_penalty_per_position():
    with pytest.raises(ValueError):
        TeamSizeRestriction(expected_size=5, penalty_per_position=0.0)
    with pytest.raises(ValueError):
        TeamSizeRestriction(expected_size=5, penalty_per_position=-1.0)

def test_team_size_requires_at_least_one_team():
    restriction = TeamSizeRestriction(expected_size=5)
    with pytest.raises(ValueError, match="At least one team is required"):
        restriction.evaluate([])
