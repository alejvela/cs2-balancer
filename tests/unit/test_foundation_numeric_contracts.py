from dataclasses import replace

import pytest

from models.numeric import finite_real
from models.player import Player
from objective.objective_result import ObjectiveResult
from objective.restriction_result import RestrictionResult
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
    GlobalBoundResult,
    PowerTeamInterval,
)
from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.global_search.global_player_ordering import GlobalPlayerOrdering
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalTeamState,
)

INVALID = [float("nan"), float("inf"), float("-inf"), True, False]


def error_for(value):
    return TypeError if isinstance(value, bool) else ValueError


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize("field", ["score", "penalty", "weight"])
def test_restriction_rejects_invalid_decision_numbers(field, value):
    values = dict(name="test", score=50, penalty=0, weight=1)
    values[field] = value
    with pytest.raises(error_for(value), match=field):
        RestrictionResult(**values)


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize("field", ["score", "penalty", "weight"])
@pytest.mark.parametrize("zero_weight", [False, True])
def test_objective_revalidates_mutated_restrictions_before_shortcuts(
    field, value, zero_weight
):
    restriction = RestrictionResult("test", 50, weight=0 if zero_weight else 1)
    result = ObjectiveResult({"test": restriction})
    setattr(restriction, field, value)
    with pytest.raises(error_for(value), match=field):
        result.compute()
    with pytest.raises(error_for(value), match=field):
        ObjectiveResult().add_result(restriction)
    with pytest.raises(error_for(value), match=field):
        _ = result.weighted_average


@pytest.mark.parametrize("value", INVALID)
def test_objective_rejects_invalid_final_score(value):
    with pytest.raises(error_for(value), match="score"):
        ObjectiveResult(score=value)
    with pytest.raises(error_for(value), match="score"):
        ObjectiveResult._clamp_score(value)
    result = ObjectiveResult()
    result.score = value
    with pytest.raises(error_for(value), match="score"):
        result.compute()


@pytest.mark.parametrize(
    "field,property_name",
    [("score", "weighted_score"), ("weight", "total_weight"), ("penalty", "penalty")],
)
@pytest.mark.parametrize("value", INVALID)
def test_aggregate_properties_reject_invalid_components(field, property_name, value):
    restriction = RestrictionResult("test", 50)
    setattr(restriction, field, value)
    with pytest.raises(error_for(value)):
        getattr(ObjectiveResult({"test": restriction}), property_name)


@pytest.mark.parametrize(
    "property_name,score,weight,penalty",
    [
        ("weighted_score", 100, 1e308, 0),
        ("weighted_score", 1, 1e308, 0),
        ("total_weight", 0, 1e308, 0),
        ("penalty", 0, 1, 1e308),
    ],
)
def test_finite_components_cannot_overflow_objective_aggregation(
    property_name, score, weight, penalty
):
    result = ObjectiveResult(
        {name: RestrictionResult(name, score, penalty, weight) for name in ("a", "b")}
    )
    with pytest.raises(ValueError, match="finite"):
        getattr(result, property_name)
    with pytest.raises(ValueError, match="finite"):
        result.compute()


def test_finite_clamping_and_zero_weight_contracts_are_preserved():
    assert RestrictionResult("low", -1).score == 0
    assert RestrictionResult("high", 101).score == 100
    assert (
        ObjectiveResult(
            {"a": RestrictionResult("a", 100, penalty=5, weight=0)}
        ).compute()
        == 0
    )
    assert ObjectiveResult({"a": RestrictionResult("a", 10, penalty=20)}).compute() == 0


def test_unrepresentable_integer_fails_explicitly():
    with pytest.raises(ValueError, match="finite"):
        finite_real(10**1000, "value")


def test_weighted_average_rejects_overflow_from_custom_restriction():
    class CustomResult(RestrictionResult):
        @property
        def weighted_score(self):
            return 1e308

    result = ObjectiveResult({"custom": CustomResult("custom", 1, weight=1e-308)})
    with pytest.raises(ValueError, match="weighted_average"):
        _ = result.weighted_average
    with pytest.raises(ValueError, match="score"):
        result.compute()


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize("field", ["power", "elo", "kd"])
def test_global_metrics_reject_invalid_numbers(field, value):
    values = dict(power=1, elo=1, kd=1, seed=None)
    values[field] = value
    with pytest.raises(error_for(value), match=field):
        GlobalPlayerMetrics(Player("a"), **values)


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize("field", ["power_sum", "elo_sum", "kd_sum"])
def test_global_team_sums_reject_invalid_numbers(field, value):
    with pytest.raises(error_for(value), match=field):
        GlobalTeamState(**{field: value})


@pytest.mark.parametrize(
    "field,metric", [("power_sum", "power"), ("elo_sum", "elo"), ("kd_sum", "kd")]
)
def test_global_assignment_rejects_overflow_without_mutating_state(field, metric):
    state = GlobalTeamState(**{field: 1e308})
    values = dict(power=1, elo=1, kd=1, seed=None)
    values[metric] = 1e308
    with pytest.raises(ValueError, match=field):
        state.add_player(0, GlobalPlayerMetrics(Player("a"), **values), None)
    assert state.player_indices == ()


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize(
    "field", ["maximum_elapsed_seconds", "score_tolerance", "minimum_improvement"]
)
def test_global_config_rejects_invalid_numbers(field, value):
    with pytest.raises(error_for(value), match=field):
        GlobalOptimizationConfig(**{field: value})


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize("method", ["score_improves", "scores_equivalent"])
@pytest.mark.parametrize("position", [0, 1])
def test_global_comparisons_reject_invalid_operands(value, method, position):
    values = [50, 50]
    values[position] = value
    with pytest.raises(error_for(value)):
        getattr(GlobalOptimizationConfig(), method)(*values)


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize(
    "field", ["power_weight", "elo_weight", "kd_weight", "seed_bonus"]
)
def test_ordering_config_rejects_invalid_numbers(field, value):
    with pytest.raises(error_for(value), match=field):
        GlobalPlayerOrdering(**{field: value})


def test_ordering_rejects_population_overflow():
    players = [
        GlobalPlayerMetrics(Player(name), 1e308, 1, 1, None) for name in ("a", "b")
    ]
    with pytest.raises(ValueError, match="finite"):
        GlobalPlayerOrdering().order(players)


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize(
    "field",
    [
        "power_weight",
        "elo_balance_weight",
        "elo_spread_weight",
        "kd_weight",
        "team_size_weight",
        "seed_weight",
        "score_tolerance",
    ],
)
def test_bound_config_rejects_invalid_numbers(field, value):
    with pytest.raises(error_for(value), match=field):
        GlobalBoundCalculator(**{field: value})


def test_bound_config_rejects_total_weight_overflow():
    with pytest.raises(ValueError, match="total_weight"):
        GlobalBoundCalculator(power_weight=1e308, kd_weight=1e308)


def test_bound_aggregation_rejects_overflow_before_clamping():
    calculator = GlobalBoundCalculator(power_weight=1e308)
    with pytest.raises(ValueError, match="finite"):
        calculator._combine_upper_bounds(100, 100, 100)


@pytest.mark.parametrize("value", INVALID)
def test_restriction_passed_revalidates_mutated_penalty(value):
    result = RestrictionResult("test", 50)
    result.penalty = value
    with pytest.raises(error_for(value), match="penalty"):
        _ = result.passed


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize(
    "field",
    [
        "current_power_sum",
        "minimum_total",
        "maximum_total",
        "minimum_average",
        "maximum_average",
    ],
)
def test_power_interval_rejects_invalid_numbers(field, value):
    interval = PowerTeamInterval(0, 0, 1, 0, 0, 1, 0, 1)
    with pytest.raises(error_for(value), match=field):
        replace(interval, **{field: value})
    with pytest.raises(error_for(value), match="interval value"):
        interval.contains(value)


@pytest.mark.parametrize("value", INVALID)
@pytest.mark.parametrize(
    "field",
    [
        "upper_bound",
        "incumbent_score",
        "power_upper_bound",
        "elo_upper_bound",
        "kd_upper_bound",
        "minimum_unavoidable_power_spread",
        "minimum_unavoidable_power_stddev",
    ],
)
def test_bound_result_rejects_invalid_numbers(field, value):
    result = GlobalBoundResult(True, 100, False, None, 50, 0, True, True, 100, 100, 100)
    with pytest.raises(error_for(value), match=field):
        replace(result, **{field: value})
