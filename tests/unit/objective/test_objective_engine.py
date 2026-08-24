from __future__ import annotations

import pytest

from objective.objective_engine import ObjectiveEngine
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult


class FixedRestriction(Restriction):
    def __init__(self, name, score, weight, penalty=0.0):
        super().__init__(weight=weight)
        self._name = name
        self._score = float(score)
        self._penalty = float(penalty)
        self.calls = 0
        self.received_teams = None

    @property
    def name(self):
        return self._name

    def evaluate(self, teams):
        self.calls += 1
        self.received_teams = teams
        return RestrictionResult(
            name=self.name,
            score=self._score,
            weight=self.weight,
            penalty=self._penalty,
        )


class InvalidReturnRestriction(FixedRestriction):
    def evaluate(self, teams):
        return 123.0


def test_engine_evaluates_every_restriction_once(team_factory):
    teams = [team_factory(1), team_factory(2)]
    first = FixedRestriction("First", 100.0, 60.0)
    second = FixedRestriction("Second", 50.0, 40.0)

    engine = ObjectiveEngine([first, second])
    result = engine.evaluate(teams)

    assert first.calls == 1
    assert second.calls == 1
    assert first.received_teams == teams
    assert second.received_teams == teams
    assert result.score == pytest.approx(80.0)


def test_engine_applies_penalty_after_weighted_average(team_factory):
    engine = ObjectiveEngine([
        FixedRestriction("Soft", 100.0, 90.0),
        FixedRestriction("Hard", 100.0, 10.0, penalty=15.0),
    ])

    result = engine.evaluate([team_factory(1), team_factory(2)])

    assert result.weighted_average == pytest.approx(100.0)
    assert result.penalty == pytest.approx(15.0)
    assert result.score == pytest.approx(85.0)
    assert result.is_valid is False


def test_engine_rejects_none_restrictions():
    with pytest.raises(ValueError, match="restrictions cannot be None"):
        ObjectiveEngine(None)


def test_engine_rejects_empty_restrictions():
    with pytest.raises(ValueError, match="At least one restriction is required"):
        ObjectiveEngine([])


def test_engine_rejects_duplicate_names():
    with pytest.raises(ValueError, match="Duplicated restriction name"):
        ObjectiveEngine([
            FixedRestriction("Power", 100.0, 50.0),
            FixedRestriction("power", 100.0, 50.0),
        ])


def test_engine_rejects_none_teams():
    engine = ObjectiveEngine([FixedRestriction("A", 100.0, 1.0)])

    with pytest.raises(ValueError, match="teams cannot be None"):
        engine.evaluate(None)


def test_engine_rejects_empty_teams():
    engine = ObjectiveEngine([FixedRestriction("A", 100.0, 1.0)])

    with pytest.raises(ValueError, match="At least one team is required"):
        engine.evaluate([])


def test_engine_rejects_none_team_inside_collection(team_factory):
    engine = ObjectiveEngine([FixedRestriction("A", 100.0, 1.0)])

    with pytest.raises(ValueError, match="Team 2 cannot be None"):
        engine.evaluate([team_factory(1), None])


def test_engine_rejects_wrong_restriction_result_type(team_factory):
    engine = ObjectiveEngine([
        InvalidReturnRestriction("Broken", 100.0, 1.0)
    ])

    with pytest.raises(TypeError, match="must return a RestrictionResult"):
        engine.evaluate([team_factory(1), team_factory(2)])
