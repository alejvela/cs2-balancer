"""SCRUM-51: operation budgets, truthful termination and result/report parity."""

from dataclasses import replace

import pytest

from application.results.global_report_result import GlobalReportResult
from objective.objective_result import ObjectiveResult
from optimizer.global_search.global_bound_calculator import GlobalBoundCalculator
from optimizer.global_search.global_optimizer import GlobalOptimizer
from tests.unit.optimizer.global_search.test_global_bound_proof_contracts import (
    fixture,
    oracle,
    valid_distributions,
)
from tests.unit.optimizer.global_search.test_global_input_config_contracts import (
    RecordingObjective,
    incumbent,
    make_problem,
    search_config,
    solver,
)
from tests.unit.optimizer.global_search.test_global_optimizer import complete_problem


def run(**limits):
    problem = make_problem()
    return solver(**limits).optimize(problem, incumbent(problem))


@pytest.mark.parametrize("budget", ["maximum_nodes", "maximum_evaluations"])
def test_exact_full_tree_budget_is_exhaustion_and_replay_is_deterministic(budget):
    full = run()
    count = full.nodes_visited if budget == "maximum_nodes" else full.complete_solutions_evaluated
    exact = run(**{budget: count})
    replay = run(**{budget: count})
    assert exact.search_exhausted and not exact.stopped_by_limit
    assert exact.optimality_proven
    for result in (exact, replay):
        assert {k: v for k, v in result.as_dict().items() if k != "elapsed_seconds"} == {
            k: v for k, v in full.as_dict().items() if k != "elapsed_seconds"
        }
    short = run(**{budget: count - 1})
    assert short.stopped_by_limit and not short.search_exhausted
    assert not short.optimality_proven


def test_one_node_complete_root_can_evaluate_and_exhaust_both_budgets():
    problem = complete_problem()
    objective = RecordingObjective()
    result = solver(objective, use_incumbent=False, maximum_nodes=1,
                    maximum_evaluations=1).optimize(problem)
    assert result.nodes_visited == result.complete_solutions_evaluated == 1
    assert result.search_exhausted and not result.stopped_by_limit
    assert len(objective.calls) == 2  # DFS and independent final evaluation.


@pytest.mark.parametrize("budget,reason", [
    ("maximum_nodes", "NODE_LIMIT"), ("maximum_evaluations", "EVALUATION_LIMIT"),
])
def test_one_unit_interruption_is_not_a_proof(budget, reason):
    result = run(**{budget: 1})
    assert result.stop_reason == reason
    assert result.stopped_by_limit and not result.search_exhausted
    assert not result.optimality_proven
    assert getattr(result, "nodes_visited" if budget == "maximum_nodes"
                   else "complete_solutions_evaluated") == 1


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.mark.parametrize("phase", ["validation", "incumbent", "witness", "dfs", "final", "certificate"])
def test_total_time_includes_each_phase_and_only_pending_search_is_limited(monkeypatch, phase):
    import optimizer.global_search.global_optimizer as module

    clock = Clock()
    monkeypatch.setattr(module, "perf_counter", clock)
    problem = complete_problem()

    class Objective(RecordingObjective):
        def evaluate(self, teams):
            value = super().evaluate(teams)
            # incumbent, canonical witness, DFS, final verification
            if len(self.calls) == {"incumbent": 1, "witness": 2, "dfs": 3, "final": 4}.get(phase):
                clock.now += 5
            return value

    optimizer = solver(Objective(), maximum_elapsed_seconds=1)
    if phase == "validation":
        original = optimizer._validate_incumbent

        def validate(*args):
            clock.now += 5
            return original(*args)

        monkeypatch.setattr(optimizer, "_validate_incumbent", validate)
    if phase == "certificate":
        original = module.GlobalProofCertificate

        def certificate(**kwargs):
            clock.now += 5
            return original(**kwargs)

        monkeypatch.setattr(module, "GlobalProofCertificate", certificate)
    result = optimizer.optimize(problem, incumbent(problem, groups=((0,), (1,))))
    assert result.elapsed_seconds == 5
    if phase in ("validation", "incumbent", "witness"):
        assert result.stop_reason == "TIME_LIMIT" and result.nodes_visited == 0
    else:
        # Finishing the final atomic operation is exhaustion, even after deadline.
        assert result.search_exhausted and not result.stopped_by_limit


def test_final_verification_deadline_does_not_revoke_a_completed_proof(monkeypatch):
    expected_calls = run().complete_solutions_evaluated + 3
    clock = Clock()
    monkeypatch.setattr("optimizer.global_search.global_optimizer.perf_counter", clock)

    class Objective(RecordingObjective):
        def evaluate(self, teams):
            score = super().evaluate(teams)
            if len(self.calls) == expected_calls:
                clock.now = 5
            return score

    problem = make_problem()
    result = solver(Objective(), maximum_elapsed_seconds=1).optimize(problem, incumbent(problem))
    assert result.elapsed_seconds == 5
    assert result.search_exhausted and result.optimality_proven
    assert result.stop_reason == "SEARCH_EXHAUSTED"


def test_deadline_before_leaf_evaluation_counts_admitted_node_only(monkeypatch):
    import optimizer.global_search.global_optimizer as module

    clock = Clock()
    monkeypatch.setattr(module, "perf_counter", clock)
    original = module.certified_decision

    def decision(*args):
        result = original(*args)
        clock.now = 2
        return result

    monkeypatch.setattr(module, "certified_decision", decision)
    problem = complete_problem()
    result = solver(maximum_nodes=1, maximum_elapsed_seconds=1).optimize(
        problem, incumbent(problem, groups=((0,), (1,))))
    assert result.nodes_visited == 1
    assert result.complete_solutions_evaluated == 0
    assert result.stop_reason == "TIME_LIMIT"  # Node already admitted, no NODE_LIMIT.


def test_time_expires_during_dfs_with_pending_work(monkeypatch):
    clock = Clock()
    monkeypatch.setattr("optimizer.global_search.global_optimizer.perf_counter", clock)

    class Objective(RecordingObjective):
        def evaluate(self, teams):
            score = super().evaluate(teams)
            if len(self.calls) == 3:
                clock.now = 2
            return score

    problem = make_problem()
    result = solver(Objective(), maximum_elapsed_seconds=1).optimize(problem, incumbent(problem))
    assert result.stop_reason == "TIME_LIMIT"
    assert result.complete_solutions_evaluated == 1
    assert not result.optimality_proven


@pytest.mark.parametrize("node_limit,expected", [(True, "NODE_LIMIT"), (False, "EVALUATION_LIMIT")])
def test_simultaneous_limits_use_node_then_evaluation_then_time(monkeypatch, node_limit, expected):
    clock = Clock()
    monkeypatch.setattr("optimizer.global_search.global_optimizer.perf_counter", clock)
    optimizer = solver(maximum_nodes=1 if node_limit else None,
                       maximum_evaluations=1, maximum_elapsed_seconds=1)
    optimizer._reset(make_problem())
    optimizer._nodes_visited = optimizer._complete_evaluations = 1
    clock.now = 1
    assert optimizer._limit_reached()
    assert optimizer.stop_reason == expected


@pytest.mark.parametrize("budget,reason", [
    ("maximum_nodes", "NODE_LIMIT"), ("maximum_evaluations", "EVALUATION_LIMIT"),
    ("maximum_elapsed_seconds", "TIME_LIMIT"),
])
def test_proof_mode_never_relabels_an_operational_interruption(monkeypatch, budget, reason):
    # Public proof configs still reject budgets (SCRUM-49/50). Inject a runtime
    # limit after validation to exercise the defensive result path with real DFS.
    clock = Clock()
    monkeypatch.setattr("optimizer.global_search.global_optimizer.perf_counter", clock)
    config = search_config(require_proof=True)

    class Objective(RecordingObjective):
        def evaluate(self, teams):
            object.__setattr__(config, budget, 1)
            clock.now = 2
            return super().evaluate(teams)

    problem = make_problem()
    optimizer = GlobalOptimizer(Objective(), config, GlobalBoundCalculator(pruning_policy=config.pruning_policy))
    result = optimizer.optimize(problem, incumbent(problem))
    assert result.stop_reason == reason
    assert not result.optimality_proven and not result.search_exhausted


@pytest.mark.parametrize("field", ["nodes_visited", "complete_solutions_evaluated", "pruned_nodes",
                                   "capacity_prunes", "seed_prunes", "bound_prunes"])
@pytest.mark.parametrize("value", [-1, True, 1.5, float("nan"), float("inf")])
def test_reject_invalid_counters(field, value):
    with pytest.raises((TypeError, ValueError)):
        replace(run(), **{field: value})


@pytest.mark.parametrize("changes", [
    {"pruned_nodes": 1}, {"nodes_visited": 0},
    {"complete_solutions_evaluated": 10000},
    {"stop_reason": "unknown"}, {"stop_reason": None},
    {"stop_reason": "NODE_LIMIT"}, {"stopped_by_limit": True},
    {"optimality_proven": 1}, {"stopped_by_limit": 0},
    {"stop_reason": "PROOF_NOT_COMPLETED"},
])
def test_reject_inconsistent_results(changes):
    with pytest.raises((TypeError, ValueError)):
        replace(run(), **changes)


@pytest.mark.parametrize("value", [-1, float("inf"), -float("inf"), float("nan"), True])
def test_reject_invalid_elapsed(value):
    with pytest.raises((TypeError, ValueError)):
        replace(run(), elapsed_seconds=value)


def test_exhausted_uncertified_result_is_distinct_from_limit():
    raw = run()
    certificate = replace(raw.proof_certificate, ranking_exact=False)
    result = replace(raw, proof_certificate=certificate, optimality_proven=False,
                     stop_reason="PROOF_NOT_COMPLETED")
    assert result.search_exhausted and not result.stopped_by_limit
    with pytest.raises(ValueError, match="exhaustion"):
        replace(result, stop_reason="NODE_LIMIT", stopped_by_limit=True)
    assert replace(result, proof_certificate=None).search_exhausted


def test_report_parity_and_rejection_of_different_score_or_teams():
    raw = run(maximum_evaluations=1)
    objective = ObjectiveResult(score=raw.score)
    report = GlobalReportResult(raw.teams, objective, raw.initial_incumbent_score, raw)
    for field, value in raw.as_dict().items():
        if field not in ("proof_certificate", "incumbent_improved"):
            assert getattr(report, field) == value
    assert report.proof_certificate is raw.proof_certificate
    with pytest.raises(ValueError, match="score"):
        GlobalReportResult(raw.teams, ObjectiveResult(score=raw.score + 1), raw.initial_incumbent_score, raw)
    with pytest.raises(ValueError, match="teams"):
        GlobalReportResult(raw.teams[::-1], objective, raw.initial_incumbent_score, raw)
    with pytest.raises(TypeError, match="global_result"):
        GlobalReportResult(raw.teams, objective, None, None)


@pytest.mark.parametrize("kind", ["power", "mixed", "order"])
def test_exact_budget_optimum_matches_independent_exhaustive_oracle(kind):
    problem, objective, _ = fixture(kind)
    _, expected = oracle(problem, objective)
    initial = next(valid_distributions(problem))[1]
    config = search_config(use_symmetry_breaking=False, minimum_improvement=0)
    optimizer = GlobalOptimizer(objective, config, GlobalBoundCalculator(pruning_policy=config.pruning_policy))
    full = optimizer.optimize(problem, initial)
    bounded = GlobalOptimizer(objective, replace(config, maximum_nodes=full.nodes_visited,
                              maximum_evaluations=full.complete_solutions_evaluated),
                              GlobalBoundCalculator(pruning_policy=config.pruning_policy)).optimize(problem, initial)
    assert bounded.score == full.score == expected
    assert bounded.search_exhausted and bounded.optimality_proven
