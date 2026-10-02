"""Adversarial SCRUM-47 contracts, with real snapshots and object identity."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from application.results.optimization_result import OptimizationResult
from models.player import Player
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.local_optimizer import LocalOptimizer
from optimizer.moves.move import Move
from optimizer.moves.swap_move import SwapMove
from optimizer.optimization_history import OptimizationHistory
from optimizer.search_work import SearchWork
from optimizer.strategies.search_result import SearchResult
from optimizer.transaction_integrity_error import TransactionIntegrityError
from tests.unit.optimizer.test_local_optimizer import (
    ScriptedStrategy,
    evaluator_for,
    identity_snapshot,
    make_teams,
    optimizer_with_strategy,
    pipeline_for,
)


class AdversarialMove(Move):
    def __init__(self, apply_error=None, undo_error=None):
        self.apply_error = apply_error
        self.undo_error = undo_error
        self.undo_calls = 0

    def apply(self, teams):
        teams[0].players[0], teams[1].players[0] = (
            teams[1].players[0],
            teams[0].players[0],
        )
        if self.apply_error:
            raise self.apply_error

    def undo(self, teams):
        self.undo_calls += 1
        if self.undo_error:
            raise self.undo_error
        # Deliberately does nothing: the snapshot must do the real restoration.


@pytest.mark.parametrize("operation", [None, "apply", "evaluate"])
@pytest.mark.parametrize("undo_fails", [False, True])
@pytest.mark.parametrize("restoration", [None, "write", "validation"])
def test_temporary_transaction_failure_precedence(
    monkeypatch, operation, undo_fails, restoration
):
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    operational = LookupError("operational failure") if operation else None
    undo = ArithmeticError("undo failure") if undo_fails else None
    restore = OSError("restoration failure") if restoration else None
    move = AdversarialMove(operational if operation == "apply" else None, undo)
    evaluator, _ = evaluator_for({"A": 20, "B": 90})
    if operation == "evaluate":
        monkeypatch.setattr(
            evaluator.objective, "evaluate", Mock(side_effect=operational)
        )
    if restoration == "validation":
        # _restore is a classmethod; validation dispatches through the class.
        monkeypatch.setattr(
            MoveEvaluator, "_validate_restoration", Mock(side_effect=restore)
        )
    restore_call = Mock(wraps=evaluator._restore)
    if restoration == "write":
        restore_call.side_effect = restore
    monkeypatch.setattr(evaluator, "_restore", restore_call)

    if restoration:
        with pytest.raises(TransactionIntegrityError) as caught:
            evaluator.evaluate(move, teams)
        assert caught.value.__cause__ is restore
        assert caught.value.operation_error is operational
        assert caught.value.undo_error is (undo if operation != "apply" else None)
    elif operational:
        with pytest.raises(LookupError) as caught:
            evaluator.evaluate(move, teams)
        assert caught.value is operational
        if undo_fails and operation == "evaluate":
            assert caught.value.undo_error is undo
            assert "snapshot restored" in " ".join(caught.value.__notes__)
        assert identity_snapshot(teams) == before
    elif undo_fails:
        with pytest.raises(RuntimeError, match="undo.*failed") as caught:
            evaluator.evaluate(move, teams)
        assert not isinstance(caught.value, TransactionIntegrityError)
        assert caught.value.__cause__ is undo
        assert identity_snapshot(teams) == before
    else:
        assert evaluator.evaluate(move, teams).score == 90
        assert identity_snapshot(teams) == before

    assert restore_call.call_count == 1
    assert move.undo_calls == (0 if operation == "apply" else 1)


@pytest.mark.parametrize("operation", ["apply", "evaluate", "structure"])
@pytest.mark.parametrize("rollback", [None, "write", "identity", "pool"])
def test_definitive_move_rollback_precedence(monkeypatch, operation, rollback):
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    operational = LookupError("commit operation failed")
    move = AdversarialMove(operational if operation == "apply" else None)
    evaluator, _ = evaluator_for({"A": 20, "B": 90})
    optimizer = LocalOptimizer(
        evaluator,
        pipeline_for(ScriptedStrategy([SearchResult.from_move(move, 20, 90)])),
    )
    if operation == "evaluate":
        monkeypatch.setattr(
            evaluator,
            "current",
            Mock(side_effect=[evaluator.current(teams), operational]),
        )
    real_validate = optimizer._validate_structure

    def validate(*, teams, expected, stage):
        if operation == "structure" and "after applying" in stage:
            raise operational
        if rollback == "pool" and "rollback" in stage:
            raise restoration_error
        real_validate(teams=teams, expected=expected, stage=stage)

    monkeypatch.setattr(optimizer, "_validate_structure", validate)
    restoration_error = OSError("rollback failed")
    if rollback == "identity":
        monkeypatch.setattr(
            LocalOptimizer,
            "_validate_snapshot_restoration",
            Mock(side_effect=restoration_error),
        )
    restore_call = Mock(wraps=optimizer._restore)
    if rollback == "write":
        restore_call.side_effect = restoration_error
    monkeypatch.setattr(optimizer, "_restore", restore_call)

    if rollback:
        with pytest.raises(TransactionIntegrityError) as caught:
            optimizer.optimize(teams)
        assert caught.value.__cause__ is restoration_error
        assert caught.value.operation_error is operational
    else:
        with pytest.raises(LookupError) as caught:
            optimizer.optimize(teams)
        assert caught.value is operational
        assert identity_snapshot(teams) == before
    assert restore_call.call_count == 1
    assert move.undo_calls == 0


@pytest.mark.parametrize("attempts", [1, 4])
def test_no_move_work_and_zero_accepted_summary(attempts):
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy([SearchResult.no_move(72, 100, 0.25)] * attempts),
        {"A": 72, "B": 90},
        max_iterations=attempts,
        stop_when_no_move=False,
    )
    result = optimizer.optimize(make_teams("A", "B"))
    assert result.initial_score == result.final_score == 72
    assert result.accepted_movements == result.history.count == 0
    assert result.total_evaluations == 100 * attempts
    assert result.history.total_elapsed == 0.25 * attempts
    assert result.history.best_iteration is result.history.worst_iteration is None
    for summary in (
        result.history.phase_summary(),
        result.history.strategy_summary(),
        result.history.neighborhood_summary(),
    ):
        (group,) = summary.values()
        assert group["iterations"] == group["improvement"] == 0
        assert group["searches"] == attempts
        assert group["evaluations"] == 100 * attempts
        assert group["elapsed"] == 0.25 * attempts
    serialized = result.as_dict()
    assert len(serialized["history"]["search_work"]) == attempts
    assert serialized["history"]["iterations"] == []


def test_mixed_search_work_counts_each_attempt_once():
    teams = make_teams("A", "B")
    move = SwapMove(teams[0], teams[0].players[0], teams[1], teams[1].players[0])
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy(
            [
                SearchResult.no_move(20, 3, 0.125),
                SearchResult.from_move(move, 20, 90, 7, 0.25),
                SearchResult.no_move(90, 11, 0.5),
            ]
        ),
        {"A": 20, "B": 90},
        max_iterations=3,
        stop_when_no_move=False,
    )
    result = optimizer.optimize(teams)
    assert result.iterations == 1
    assert result.total_evaluations == 21
    assert result.history.total_elapsed == 0.875
    assert result.history.phase_summary()["Test phase"]["searches"] == 3
    assert result.history[0].evaluations == 7
    legacy_history = OptimizationHistory(result.history.iterations)
    assert legacy_history.total_evaluations == 7
    legacy_history.extend(result.history.iterations)
    assert legacy_history.total_evaluations == 14
    result.history.clear()
    assert result.history.search_work == ()
    assert result.history.count == result.history.total_evaluations == 0


def test_result_requires_explicit_authoritative_initial_score():
    teams = make_teams("A", "B")
    evaluator, _ = evaluator_for({"A": 72, "B": 90})
    objective = evaluator.current(teams).objective_result
    history = OptimizationHistory()
    with pytest.raises(TypeError, match="initial_score"):
        OptimizationResult(teams, objective, history)
    with pytest.raises(TypeError, match="initial_score"):
        OptimizationResult.from_history(teams, objective, history)
    result = OptimizationResult.from_history(
        teams, objective, history, initial_score=50
    )
    assert result.initial_score == 50
    assert result.final_score == 72
    assert result.improvement == 22
    assert result.as_dict()["initial_score"] == 50


@pytest.mark.parametrize(
    "field", ["score_before", "score_after", "evaluations", "elapsed"]
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
def test_search_result_rejects_non_finite_and_boolean_values(field, value):
    values = dict(
        move=None, score_before=72, score_after=72, evaluations=100, elapsed=0.1
    )
    values[field] = value
    with pytest.raises((ValueError, TypeError)):
        SearchResult(**values)


@pytest.mark.parametrize(
    "field,value",
    [
        ("evaluations", -1),
        ("evaluations", 1.5),
        ("evaluations", True),
        ("evaluations", float("nan")),
        ("elapsed", -1),
        ("elapsed", float("inf")),
        ("elapsed", True),
    ],
)
def test_search_work_validates_metrics(field, value):
    values = dict(phase="p", strategy="s", neighborhood="n", evaluations=1, elapsed=0.1)
    values[field] = value
    with pytest.raises((ValueError, TypeError)):
        SearchWork(**values)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_result_rejects_invalid_initial_score(value):
    teams = make_teams("A")
    evaluator, _ = evaluator_for({"A": 72})
    with pytest.raises((ValueError, TypeError)):
        OptimizationResult(
            teams,
            evaluator.current(teams).objective_result,
            OptimizationHistory(),
            initial_score=value,
        )


@pytest.mark.parametrize("fallback_score", [72, 71, 72 - 0.5e-9])
def test_final_independent_evaluation_and_initial_fallback(monkeypatch, fallback_score):
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    optimizer, _ = optimizer_with_strategy(ScriptedStrategy([]), {"A": 72, "B": 90})
    evaluator = optimizer.evaluator
    real_evaluation = evaluator.current(teams)
    final = evaluator.current(teams)
    final.objective_result.score = fallback_score
    current = Mock(
        side_effect=[real_evaluation, real_evaluation, SimpleNamespace(score=60), final]
    )
    monkeypatch.setattr(evaluator, "current", current)
    if fallback_score < 72 - LocalOptimizer.SCORE_TOLERANCE:
        with pytest.raises(RuntimeError, match="at least as good"):
            optimizer.optimize(teams)
    else:
        result = optimizer.optimize(teams)
        assert result.initial_score == 72
        assert result.final_score == fallback_score
        assert (
            result.final_score >= result.initial_score - LocalOptimizer.SCORE_TOLERANCE
        )
    assert current.call_count == 4
    assert identity_snapshot(teams) == before


@pytest.mark.parametrize("call", [1, 2, 3])
def test_local_rejects_non_finite_authoritative_scores(monkeypatch, call):
    teams = make_teams("A", "B")
    optimizer, _ = optimizer_with_strategy(ScriptedStrategy([]), {"A": 72, "B": 90})
    good = optimizer.evaluator.current(teams)
    monkeypatch.setattr(
        optimizer.evaluator,
        "current",
        Mock(side_effect=[*([good] * (call - 1)), SimpleNamespace(score=float("nan"))]),
    )
    with pytest.raises(ValueError, match="finite"):
        optimizer.optimize(teams)


@pytest.mark.parametrize(
    "validation", [MoveEvaluator._restore, LocalOptimizer._restore]
)
@pytest.mark.parametrize("corruption", ["equal_copy", "order"])
def test_real_restoration_checks_exact_identity_and_order(validation, corruption):
    teams = make_teams("A", "B")
    teams[0].players.append(Player("C"))
    snapshot = MoveEvaluator._snapshot(teams)

    class DishonestList(list):
        def __setitem__(self, key, value):
            if isinstance(key, slice):
                value = list(value)
                if corruption == "equal_copy":
                    value[0] = Player(value[0].nick)
                else:
                    value.reverse()
            super().__setitem__(key, value)

    teams[0].players = DishonestList(teams[0].players)
    with pytest.raises(RuntimeError, match="position 1"):
        validation(teams, snapshot)


def test_non_finite_definitive_score_rolls_back(monkeypatch):
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    move = AdversarialMove()
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy([SearchResult.from_move(move, 20, 90)]), {"A": 20, "B": 90}
    )
    initial = optimizer.evaluator.current(teams)
    monkeypatch.setattr(
        optimizer.evaluator,
        "current",
        Mock(side_effect=[initial, SimpleNamespace(score=float("nan"))]),
    )
    with pytest.raises(ValueError, match="finite"):
        optimizer.optimize(teams)
    assert identity_snapshot(teams) == before


def test_accepted_result_cannot_be_recorded_as_no_move():
    history = OptimizationHistory()
    with pytest.raises(ValueError, match="Use add"):
        history.add_no_move(
            phase="p",
            strategy="s",
            neighborhood="n",
            result=SearchResult.from_move(AdversarialMove(), 20, 90),
        )
    assert history.search_work == ()


def test_best_snapshot_is_independently_reevaluated(monkeypatch):
    teams = make_teams("A", "B", "C")
    a, b, c = (team.players[0] for team in teams)
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy(
            [
                SearchResult.from_move(SwapMove(teams[0], a, teams[1], b), 40, 90),
                SearchResult.from_move(SwapMove(teams[0], b, teams[2], c), 90, 20),
            ]
        ),
        {"A": 40, "B": 90, "C": 20},
        max_iterations=2,
    )
    delegate = optimizer.evaluator.current
    evaluated_states = []

    def current(teams):
        evaluated_states.append(identity_snapshot(teams))
        return delegate(teams)

    monkeypatch.setattr(optimizer.evaluator, "current", current)
    result = optimizer.optimize(teams)
    assert len(evaluated_states) == 5  # initial, two commits, phase, final
    assert evaluated_states[-1] == evaluated_states[-2] == evaluated_states[1]
    assert result.initial_score == 40
    assert result.final_score == 90
    assert result.improvement == 50
    assert result.history.final_score == 20
