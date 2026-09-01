from __future__ import annotations

from models.player import Player
from models.team import Team
from objective.objective_result import ObjectiveResult
from objective.restriction_result import RestrictionResult
from optimizer.modes.stable_optimization_config import StableOptimizationConfig
from optimizer.moves.move import Move
from optimizer.optimization_history import OptimizationHistory
from optimizer.optimization_iteration import OptimizationIteration
from optimizer.optimization_result import OptimizationResult
from optimizer.stable.convergence_tracker import ConvergenceTracker
from optimizer.strategies.search_result import SearchResult


class NoOpMove(Move):
    def apply(self, teams) -> None:
        pass

    def undo(self, teams) -> None:
        pass


def config(**overrides) -> StableOptimizationConfig:
    values = {
        "target_score": 90,
        "maximum_restarts": 6,
        "minimum_restarts": 3,
        "convergence_patience": 2,
        "minimum_unique_solutions": 2,
        "target_confirmation_restarts": 2,
        "stop_on_perfect_score": False,
    }
    values.update(overrides)
    return StableOptimizationConfig(**values)


def result(
    groups: tuple[tuple[str, ...], ...],
    score: float,
    *,
    penalty: float = 0,
    evaluations: int = 0,
    elapsed: float = 0,
) -> OptimizationResult:
    teams = [
        Team(index, [Player(name) for name in group])
        for index, group in enumerate(groups, 1)
    ]
    objective = ObjectiveResult()
    objective.add_result(RestrictionResult("Quality", score, penalty=penalty))
    objective.score = score
    history = OptimizationHistory()
    if evaluations or elapsed:
        history.add(
            OptimizationIteration(
                phase="test",
                iteration=1,
                strategy="scripted",
                neighborhood="scripted",
                result=SearchResult.from_move(
                    NoOpMove(),
                    score_before=score,
                    score_after=score,
                    evaluations=evaluations,
                    elapsed=elapsed,
                ),
            )
        )
    return OptimizationResult(teams, objective, history)


GROUP_A = (("A", "B"), ("C", "D"))
GROUP_B = (("A", "C"), ("B", "D"))
GROUP_C = (("A", "D"), ("B", "C"))


def test_first_registration_is_recorded_as_quality_improvement():
    tracker = ConvergenceTracker(config())

    record = tracker.register(result(GROUP_A, 50), 0, 100, improved_best=True)

    assert record.improved_best is True
    assert tracker.best_restart_index == 0
    assert tracker.restarts_without_improvement == 0


def test_genuine_score_and_penalty_improvements_reset_patience():
    tracker = ConvergenceTracker(config())
    tracker.register(result(GROUP_A, 50, penalty=5), 0, 10, improved_best=True)
    tracker.register(result(GROUP_B, 40, penalty=5), 1, 11, improved_best=False)
    assert tracker.restarts_without_improvement == 1

    tracker.register(result(GROUP_C, 30, penalty=1), 2, 12, improved_best=True)

    assert tracker.restarts_without_improvement == 0
    assert tracker.best_restart_index == 2


def test_duplicate_signature_counts_restart_and_no_improvement_but_not_unique():
    tracker = ConvergenceTracker(config())
    tracker.register(result(GROUP_A, 50), 0, 10, improved_best=True)

    tracker.register(result((("D", "C"), ("B", "A")), 50), 1, 11, improved_best=False)

    assert tracker.completed_restarts == 2
    assert tracker.unique_solution_count == 1
    assert tracker.restarts_without_improvement == 1


def test_equal_score_new_signature_and_worse_unique_candidate_advance_patience():
    tracker = ConvergenceTracker(config())
    tracker.register(result(GROUP_A, 50), 0, 10, improved_best=True)
    tracker.register(result(GROUP_B, 50), 1, 11, improved_best=False)
    tracker.register(result(GROUP_C, 40), 2, 12, improved_best=False)

    assert tracker.unique_solution_count == 3
    assert tracker.restarts_without_improvement == 2


def test_convergence_requires_minimum_restarts_patience_and_unique_solutions():
    tracker = ConvergenceTracker(
        config(minimum_restarts=3, convergence_patience=2, minimum_unique_solutions=3)
    )
    tracker.register(result(GROUP_A, 50), 0, 10, improved_best=True)
    tracker.register(result(GROUP_B, 50), 1, 11, improved_best=False)
    assert tracker.convergence_reached is False

    tracker.register(result(GROUP_C, 50), 2, 12, improved_best=False)

    assert tracker.completed_restarts == 3
    assert tracker.restarts_without_improvement == 2
    assert tracker.unique_solution_count == 3
    assert tracker.convergence_reached is True


def test_target_confirmation_counts_only_restarts_after_target_and_respects_minimum():
    tracker = ConvergenceTracker(
        config(
            maximum_restarts=5,
            minimum_restarts=3,
            convergence_patience=5,
            minimum_unique_solutions=0,
            target_confirmation_restarts=2,
        )
    )
    tracker.register(result(GROUP_A, 90), 0, 10, improved_best=True)
    assert tracker.restarts_since_target == 0
    assert tracker.target_confirmed is False
    tracker.register(result(GROUP_B, 80), 1, 11, improved_best=False)
    assert tracker.restarts_since_target == 1
    assert tracker.target_confirmed is False

    tracker.register(result(GROUP_C, 80), 2, 12, improved_best=False)

    assert tracker.restarts_since_target == 2
    assert tracker.target_confirmed is True
    assert tracker.stop_reason == "target_confirmed"


def test_perfect_score_stop_requires_enabled_setting_observation_and_minimum_search():
    tracker = ConvergenceTracker(
        config(
            maximum_restarts=4,
            minimum_restarts=3,
            convergence_patience=4,
            minimum_unique_solutions=0,
            stop_on_perfect_score=True,
        )
    )
    tracker.register(result(GROUP_A, 100), 0, 10, improved_best=True)
    assert tracker.perfect_was_reached is True
    assert tracker.perfect_stop_reached is False
    tracker.register(result(GROUP_B, 80), 1, 11, improved_best=False)
    assert tracker.perfect_stop_reached is False

    tracker.register(result(GROUP_C, 80), 2, 12, improved_best=False)

    assert tracker.perfect_stop_reached is True
    assert tracker.stop_reason == "perfect_score"


def test_evaluation_limit_can_stop_before_minimum_and_after_overshooting_boundary():
    tracker = ConvergenceTracker(
        config(maximum_total_evaluations=5, minimum_restarts=4)
    )
    tracker.register(result(GROUP_A, 50, evaluations=6), 0, 10, improved_best=True)

    assert tracker.completed_restarts == 1
    assert tracker.total_evaluations == 6
    assert tracker.evaluation_limit_reached is True
    assert tracker.stop_reason == "evaluation_limit"


def test_elapsed_limit_can_stop_before_minimum_without_freezing_duration():
    tracker = ConvergenceTracker(
        config(maximum_elapsed_seconds=0.01, minimum_restarts=4)
    )
    tracker._started_at -= 1.0
    tracker.register(result(GROUP_A, 50), 0, 10, improved_best=True)

    assert tracker.completed_restarts == 1
    assert tracker.elapsed_limit_reached is True
    assert tracker.stop_reason == "elapsed_limit"


def test_stop_reason_uses_documented_priority_when_conditions_overlap():
    tracker = ConvergenceTracker(
        config(
            maximum_restarts=1,
            minimum_restarts=1,
            convergence_patience=1,
            minimum_unique_solutions=0,
            target_confirmation_restarts=0,
            maximum_total_evaluations=1,
            stop_on_perfect_score=True,
        )
    )
    tracker.register(result(GROUP_A, 100, evaluations=1), 0, 10, improved_best=True)

    assert tracker.stop_reason == "perfect_score"
