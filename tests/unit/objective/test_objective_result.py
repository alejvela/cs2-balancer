from __future__ import annotations

import pytest

from objective.objective_result import ObjectiveResult
from objective.restriction_result import RestrictionResult


def make_result(name, score, weight, penalty=0.0):
    return RestrictionResult(
        name=name,
        score=score,
        weight=weight,
        penalty=penalty,
    )


def test_compute_returns_weighted_average_without_penalty():
    result = ObjectiveResult()
    result.add_result(make_result("A", 100.0, 75.0))
    result.add_result(make_result("B", 40.0, 25.0))

    assert result.compute() == pytest.approx(85.0)
    assert result.weighted_average == pytest.approx(85.0)
    assert result.total_weight == pytest.approx(100.0)
    assert result.penalty == pytest.approx(0.0)
    assert result.is_valid is True


def test_compute_subtracts_penalty_after_weighting():
    result = ObjectiveResult()
    result.add_result(make_result("Soft", 100.0, 90.0))
    result.add_result(make_result("Hard", 100.0, 10.0, penalty=12.5))

    assert result.compute() == pytest.approx(87.5)
    assert result.weighted_average == pytest.approx(100.0)
    assert result.penalty == pytest.approx(12.5)
    assert result.is_valid is False


def test_compute_clamps_to_zero():
    result = ObjectiveResult()
    result.add_result(make_result("A", 10.0, 100.0, penalty=50.0))

    assert result.compute() == pytest.approx(0.0)


def test_empty_result_is_zero():
    result = ObjectiveResult()

    assert result.compute() == pytest.approx(0.0)


def test_zero_total_weight_is_zero():
    result = ObjectiveResult()
    result.add_result(make_result("A", 100.0, 0.0))

    assert result.compute() == pytest.approx(0.0)


def test_get_is_case_insensitive():
    result = ObjectiveResult()
    expected = make_result("Power Balance", 91.0, 55.0)
    result.add_result(expected)

    assert result.get("power balance") is expected
    assert result.get("POWER BALANCE") is expected
    assert result.get(" Power Balance ") is expected


def test_duplicate_names_are_rejected_case_insensitively():
    result = ObjectiveResult()
    result.add_result(make_result("Power Balance", 90.0, 55.0))

    with pytest.raises(ValueError, match="Duplicated restriction result"):
        result.add_result(make_result("power balance", 95.0, 55.0))


def test_summary_contains_scores():
    result = ObjectiveResult()
    result.add_result(make_result("Power", 97.5, 55.0))
    result.add_result(make_result("KD", 92.0, 20.0))

    assert result.summary() == {"Power": 97.5, "KD": 92.0}


def test_as_dict_contains_global_calculation():
    result = ObjectiveResult()
    result.add_result(make_result("A", 80.0, 100.0, penalty=5.0))
    result.compute()

    payload = result.as_dict()

    assert payload["score"] == pytest.approx(75.0)
    assert payload["weighted_average"] == pytest.approx(80.0)
    assert payload["total_weight"] == pytest.approx(100.0)
    assert payload["penalty"] == pytest.approx(5.0)
    assert payload["is_valid"] is False
