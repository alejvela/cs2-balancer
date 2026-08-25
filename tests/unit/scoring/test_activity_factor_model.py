from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.player import Player
from optimizer.activity.activity_factor_model import (
    ActivityEvaluation,
    ActivityFactorModel,
)
from scrapers.player_record import ActivityRecord


def make_activity(
    matches_0_7_days: int,
    matches_8_30_days: int,
    matches_31_90_days: int,
    *,
    history_complete: bool = True,
) -> ActivityRecord:
    return ActivityRecord(
        matches_0_7_days=matches_0_7_days,
        matches_8_30_days=matches_8_30_days,
        matches_31_90_days=matches_31_90_days,
        total_matches_90_days=(
            matches_0_7_days
            + matches_8_30_days
            + matches_31_90_days
        ),
        history_complete=history_complete,
    )


def test_default_configuration():
    model = ActivityFactorModel()

    assert model.minimum_factor == pytest.approx(0.75)
    assert model.weight_0_7 == pytest.approx(0.50)
    assert model.weight_8_30 == pytest.approx(0.30)
    assert model.weight_31_90 == pytest.approx(0.20)
    assert model.target_0_7 == 10
    assert model.target_8_30 == 20
    assert model.target_31_90 == 30


def test_custom_configuration():
    model = ActivityFactorModel(
        minimum_factor=0.60,
        weight_0_7=0.60,
        weight_8_30=0.25,
        weight_31_90=0.15,
        target_0_7=5,
        target_8_30=15,
        target_31_90=25,
    )

    assert model.minimum_factor == pytest.approx(0.60)
    assert model.weight_0_7 == pytest.approx(0.60)
    assert model.weight_8_30 == pytest.approx(0.25)
    assert model.weight_31_90 == pytest.approx(0.15)
    assert model.target_0_7 == 5
    assert model.target_8_30 == 15
    assert model.target_31_90 == 25


@pytest.mark.parametrize("value", [True, "0.75"])
def test_minimum_factor_rejects_non_numeric_values(value):
    with pytest.raises(TypeError, match="minimum_factor must be numeric"):
        ActivityFactorModel(minimum_factor=value)


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_minimum_factor_rejects_values_outside_zero_and_one(value):
    with pytest.raises(ValueError, match="must be between 0 and 1"):
        ActivityFactorModel(minimum_factor=value)


@pytest.mark.parametrize("field_name", ["weight_0_7", "weight_8_30", "weight_31_90"])
@pytest.mark.parametrize("value", [True, "0.5"])
def test_weights_reject_non_numeric_values(field_name, value):
    arguments = {field_name: value}

    with pytest.raises(TypeError, match=f"{field_name} must be numeric"):
        ActivityFactorModel(**arguments)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("weight_0_7", -0.01),
        ("weight_8_30", 1.01),
        ("weight_31_90", -1.0),
    ],
)
def test_weights_reject_values_outside_zero_and_one(field_name, value):
    arguments = {field_name: value}

    with pytest.raises(ValueError, match=f"{field_name} must be between 0 and 1"):
        ActivityFactorModel(**arguments)


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="weights must sum exactly 1.0"):
        ActivityFactorModel(
            weight_0_7=0.50,
            weight_8_30=0.30,
            weight_31_90=0.10,
        )


@pytest.mark.parametrize("field_name", ["target_0_7", "target_8_30", "target_31_90"])
@pytest.mark.parametrize("value", [True, 10.0, "10"])
def test_targets_reject_non_integer_values(field_name, value):
    arguments = {field_name: value}

    with pytest.raises(TypeError, match=f"{field_name} must be an integer"):
        ActivityFactorModel(**arguments)


@pytest.mark.parametrize("field_name", ["target_0_7", "target_8_30", "target_31_90"])
@pytest.mark.parametrize("value", [0, -1])
def test_targets_must_be_greater_than_zero(field_name, value):
    arguments = {field_name: value}

    with pytest.raises(ValueError, match=f"{field_name} must be greater than zero"):
        ActivityFactorModel(**arguments)


@pytest.mark.parametrize(
    "activity",
    [
        make_activity(10, 20, 30),
        make_activity(20, 40, 60),
    ],
)
def test_full_and_above_target_activity_have_no_penalty(activity):
    player = Player(nick="Active", level=6, activity=activity)

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.activity_score == pytest.approx(1.0)
    assert result.base_activity_factor == pytest.approx(1.0)
    assert result.activity_factor == pytest.approx(1.0)
    assert result.adjusted_power == pytest.approx(80.0)
    assert result.power_penalty == pytest.approx(0.0)


def test_zero_activity_uses_minimum_factor_at_level_six():
    player = Player(
        nick="Inactive",
        level=6,
        activity=make_activity(0, 0, 0),
    )

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.activity_score == pytest.approx(0.0)
    assert result.base_activity_factor == pytest.approx(0.75)
    assert result.level_penalty_strength == pytest.approx(1.0)
    assert result.activity_factor == pytest.approx(0.75)
    assert result.adjusted_power == pytest.approx(60.0)


def test_partial_activity_is_weighted_across_windows():
    player = Player(
        nick="Partial",
        level=6,
        activity=make_activity(5, 10, 15),
    )

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.activity_score == pytest.approx(0.50)
    assert result.base_activity_factor == pytest.approx(0.875)
    assert result.activity_factor == pytest.approx(0.875)
    assert result.adjusted_power == pytest.approx(70.0)


def test_missing_activity_is_neutral():
    player = Player(nick="Unknown", level=3)

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.activity_score == pytest.approx(1.0)
    assert result.base_activity_factor == pytest.approx(1.0)
    assert result.activity_factor == pytest.approx(1.0)
    assert result.adjusted_power == pytest.approx(80.0)
    assert result.faceit_level == 3
    assert result.matches_0_7_days is None


def test_activity_without_window_data_is_neutral_and_preserves_metadata():
    activity = SimpleNamespace(
        total_matches_90_days=12,
        days_since_last_match=4,
        history_complete=False,
    )
    player = SimpleNamespace(level=6, activity=activity)

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.activity_factor == pytest.approx(1.0)
    assert result.adjusted_power == pytest.approx(80.0)
    assert result.total_matches_90_days == 12
    assert result.days_since_last_match == 4
    assert result.history_complete is False


def test_missing_windows_count_as_zero_when_one_window_is_available():
    activity = SimpleNamespace(matches_0_7_days=10)
    player = SimpleNamespace(level=6, activity=activity)

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.matches_0_7_days == 10
    assert result.matches_8_30_days is None
    assert result.matches_31_90_days is None
    assert result.activity_score == pytest.approx(0.50)
    assert result.activity_factor == pytest.approx(0.875)


@pytest.mark.parametrize(
    ("level", "expected_strength", "expected_factor"),
    [
        (3, 1.14, 0.715),
        (6, 1.00, 0.750),
        (9, 0.84, 0.790),
        (None, 1.00, 0.750),
    ],
)
def test_faceit_level_adjusts_only_inactivity_penalty(
    level,
    expected_strength,
    expected_factor,
):
    player = Player(
        nick="Player",
        level=level,
        activity=make_activity(0, 0, 0),
    )

    result = ActivityFactorModel().evaluate(player, base_power=100.0)

    assert result.activity_score == pytest.approx(0.0)
    assert result.base_activity_factor == pytest.approx(0.75)
    assert result.level_penalty_strength == pytest.approx(expected_strength)
    assert result.activity_factor == pytest.approx(expected_factor)


@pytest.mark.parametrize("level", [True, "invalid", 0, 11])
def test_invalid_faceit_level_uses_unknown_level_strength(level):
    player = SimpleNamespace(
        level=level,
        activity=make_activity(0, 0, 0),
    )

    result = ActivityFactorModel().evaluate(player, base_power=100.0)

    assert result.faceit_level is None
    assert result.level_penalty_strength == pytest.approx(1.0)
    assert result.activity_factor == pytest.approx(0.75)


def test_defensive_activity_values_are_coerced_or_treated_as_missing():
    activity = SimpleNamespace(
        matches_0_7_days="5",
        matches_8_30_days=True,
        matches_31_90_days=-10,
        total_matches_90_days="invalid",
        days_since_last_match="4",
        history_complete="no",
    )
    player = SimpleNamespace(level="6", activity=activity)

    result = ActivityFactorModel().evaluate(player, base_power=80.0)

    assert result.matches_0_7_days == 5
    assert result.matches_8_30_days is None
    assert result.matches_31_90_days is None
    assert result.total_matches_90_days is None
    assert result.days_since_last_match == 4
    assert result.history_complete is False
    assert result.activity_score == pytest.approx(0.25)
    assert result.activity_factor == pytest.approx(0.8125)


@pytest.mark.parametrize("base_power", [True, "80"])
def test_evaluate_rejects_non_numeric_base_power(base_power):
    player = Player(nick="Player")

    with pytest.raises(TypeError, match="base_power must be numeric"):
        ActivityFactorModel().evaluate(player, base_power)


def test_evaluate_rejects_none_player():
    with pytest.raises(ValueError, match="player cannot be None"):
        ActivityFactorModel().evaluate(None, 80.0)


def test_negative_base_power_is_clamped_to_zero():
    player = Player(
        nick="Player",
        level=6,
        activity=make_activity(0, 0, 0),
    )

    result = ActivityFactorModel().evaluate(player, base_power=-20.0)

    assert result.base_power == pytest.approx(0.0)
    assert result.adjusted_power == pytest.approx(0.0)
    assert result.power_penalty == pytest.approx(0.0)
    assert result.power_penalty_percentage == pytest.approx(0.0)


def test_factor_returns_activity_factor_independently_of_base_power():
    player = Player(
        nick="Player",
        level=6,
        activity=make_activity(5, 10, 15),
    )
    model = ActivityFactorModel()

    assert model.factor(player) == pytest.approx(0.875)
    assert model.factor(player) == pytest.approx(
        model.evaluate(player, base_power=25.0).activity_factor
    )


def test_activity_evaluation_derived_properties_and_as_dict():
    result = ActivityEvaluation(
        activity_score=0.50,
        base_activity_factor=0.875,
        level_penalty_strength=1.0,
        activity_factor=0.875,
        base_power=80.0,
        adjusted_power=70.0,
        matches_0_7_days=5,
        matches_8_30_days=10,
        matches_31_90_days=15,
        total_matches_90_days=30,
        days_since_last_match=2,
        history_complete=True,
        faceit_level=6,
    )

    assert result.power_penalty == pytest.approx(10.0)
    assert result.power_penalty_percentage == pytest.approx(12.5)
    assert result.activity_percentage == pytest.approx(50.0)
    assert result.activity_factor_percentage == pytest.approx(87.5)
    assert result.as_dict() == {
        "activity_score": 0.50,
        "activity_percentage": 50.0,
        "base_activity_factor": 0.875,
        "level_penalty_strength": 1.0,
        "activity_factor": 0.875,
        "activity_factor_percentage": 87.5,
        "faceit_level": 6,
        "base_power": 80.0,
        "adjusted_power": 70.0,
        "power_penalty": 10.0,
        "power_penalty_percentage": 12.5,
        "matches_0_7_days": 5,
        "matches_8_30_days": 10,
        "matches_31_90_days": 15,
        "total_matches_90_days": 30,
        "days_since_last_match": 2,
        "history_complete": True,
    }


def test_history_complete_is_metadata_and_does_not_change_factor():
    complete_player = Player(
        nick="Complete",
        level=6,
        activity=make_activity(5, 10, 15, history_complete=True),
    )
    incomplete_player = Player(
        nick="Incomplete",
        level=6,
        activity=make_activity(5, 10, 15, history_complete=False),
    )
    model = ActivityFactorModel()

    complete = model.evaluate(complete_player, base_power=80.0)
    incomplete = model.evaluate(incomplete_player, base_power=80.0)

    assert complete.history_complete is True
    assert incomplete.history_complete is False
    assert complete.activity_factor == pytest.approx(incomplete.activity_factor)
    assert complete.adjusted_power == pytest.approx(incomplete.adjusted_power)


def test_repr_contains_useful_configuration():
    model = ActivityFactorModel()

    assert repr(model) == (
        "ActivityFactorModel("
        "minimum_factor=0.75, "
        "weights=(0.50, 0.30, 0.20), "
        "targets=(10, 20, 30))"
    )
