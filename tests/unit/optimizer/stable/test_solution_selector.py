from __future__ import annotations

from models.player import Player
from models.team import Team
from objective.objective_result import ObjectiveResult
from objective.restriction_result import RestrictionResult
from optimizer.modes.stable_optimization_config import StableOptimizationConfig
from optimizer.optimization_history import OptimizationHistory
from optimizer.optimization_result import OptimizationResult
from optimizer.stable.solution_selector import SolutionSelector
from optimizer.stable.solution_signature import SolutionSignature


def result(
    groups: tuple[tuple[str, ...], ...],
    score: float,
    *,
    penalty: float = 0.0,
    power_score: float | None = None,
) -> OptimizationResult:
    teams = [
        Team(index, [Player(name) for name in group])
        for index, group in enumerate(groups, 1)
    ]
    objective = ObjectiveResult()
    if power_score is not None:
        objective.add_result(RestrictionResult("Power Balance", power_score))
    objective.add_result(
        RestrictionResult("Primary", score, penalty=penalty, weight=0.0)
    )
    objective.score = score
    return OptimizationResult(teams, objective, OptimizationHistory())


def selector(tolerance: float = 1e-6) -> SolutionSelector:
    config = StableOptimizationConfig(
        maximum_restarts=2,
        minimum_restarts=1,
        convergence_patience=1,
        minimum_unique_solutions=0,
        target_confirmation_restarts=0,
        score_tolerance=tolerance,
        stop_on_perfect_score=False,
    )
    return SolutionSelector(config)


def test_first_valid_result_is_selected():
    candidate = result((("A", "B"), ("C", "D")), 50)

    assert selector().select(None, candidate) is candidate


def test_lower_structural_penalty_beats_higher_numeric_score():
    current = result((("A", "B"), ("C", "D")), 90, penalty=5)
    candidate = result((("A", "C"), ("B", "D")), 70, penalty=1)

    comparison = selector().compare(current, candidate)

    assert comparison.winner is candidate
    assert comparison.reason == "lower_structural_penalty"


def test_higher_score_outside_tolerance_wins_with_equivalent_penalty():
    current = result((("A", "B"), ("C", "D")), 80)
    candidate = result((("A", "C"), ("B", "D")), 81)

    assert selector().compare(current, candidate).winner is candidate


def test_restriction_priority_breaks_score_tie_within_tolerance():
    current = result((("A", "B"), ("C", "D")), 80, power_score=70)
    candidate = result((("A", "C"), ("B", "D")), 80.0005, power_score=90)

    comparison = selector(0.001).compare(current, candidate)

    assert comparison.winner is candidate
    assert comparison.reason == "better_restriction:Power Balance"


def test_canonical_signature_breaks_remaining_quality_tie():
    first = result((("A", "B"), ("C", "D")), 80)
    second = result((("A", "C"), ("B", "D")), 80)
    expected = min(
        (first, second), key=lambda item: SolutionSignature.from_teams(item.teams)
    )

    assert selector().compare(first, second).winner is expected


def test_identical_logical_solution_does_not_replace_current_result():
    current = result((("A", "B"), ("C", "D")), 80)
    candidate = result((("D", "C"), ("B", "A")), 80)

    comparison = selector().compare(current, candidate)

    assert comparison.winner is current
    assert comparison.same_solution is True
