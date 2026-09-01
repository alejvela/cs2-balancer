from __future__ import annotations

from itertools import combinations

import pytest

from models.player import Player
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
    GlobalBoundResult,
)
from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.global_search.global_optimization_result import GlobalOptimizationResult
from optimizer.global_search.global_optimizer import GlobalOptimizer
from optimizer.global_search.global_root_builder import GlobalRootBuilder
from optimizer.global_search.global_search_problem import GlobalSearchProblem
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
)


class ScriptedBound(GlobalBoundCalculator):
    def __init__(self, reason: str | None = None, *, failure: Exception | None = None):
        super().__init__()
        self.reason = reason
        self.failure = failure

    def evaluate(self, problem, state, incumbent_score):
        if self.failure is not None:
            raise self.failure
        prune = self.reason is not None
        return GlobalBoundResult(
            feasible=self.reason not in {"capacity_impossible", "seed_impossible"},
            upper_bound=0 if prune else 100,
            prune=prune,
            reason=self.reason,
            incumbent_score=incumbent_score,
            depth=state.depth,
            capacity_feasible=self.reason != "capacity_impossible",
            seed_feasible=self.reason != "seed_impossible",
            power_upper_bound=100,
            elo_upper_bound=100,
            kd_upper_bound=100,
        )


class IdentityObjective:
    def __init__(
        self, incumbent: SequenceTeams, incumbent_score: float, candidate_score: float
    ):
        self.incumbent = tuple(incumbent)
        self.incumbent_score = incumbent_score
        self.candidate_score = candidate_score
        self.calls: list[tuple[Team, ...]] = []

    def evaluate(self, teams):
        current = tuple(teams)
        self.calls.append(current)
        if all(
            left is right for left, right in zip(current, self.incumbent, strict=True)
        ):
            return self.incumbent_score
        return self.candidate_score


class SequenceObjective:
    def __init__(self, values):
        self.values = iter(values)

    def evaluate(self, teams):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value


class PowerOnlyRestriction(Restriction):
    @property
    def name(self) -> str:
        return "Power Balance"

    def evaluate(self, teams) -> RestrictionResult:
        averages = [
            sum(player.elo for player in team.players) / len(team.players)
            for team in teams
        ]
        global_average = sum(
            sum(player.elo for player in team.players) for team in teams
        ) / sum(len(team.players) for team in teams)
        spread = max(averages) - min(averages)
        score = (
            100
            if global_average <= 0 and spread <= 0
            else 100 * (1 - spread / global_average)
        )
        return RestrictionResult(self.name, max(0, score))


SequenceTeams = tuple[Team, ...] | list[Team]


def metric(name: str, power: float, *, seed: int | None = None) -> GlobalPlayerMetrics:
    return GlobalPlayerMetrics(
        Player(name, elo=int(power), seed=seed), power, power, 1, seed
    )


def complete_problem() -> GlobalSearchProblem:
    players = (metric("A", 10), metric("B", 20))
    state = GlobalSearchState.empty(2)
    state = state.assign_next_player(0, players[0], 1, protected_seed_level=None)
    state = state.assign_next_player(1, players[1], 1, protected_seed_level=None)
    return GlobalSearchProblem(players, state, 2, 1, protected_seed_level=None)


def branching_problem() -> GlobalSearchProblem:
    return GlobalRootBuilder(2, 2, protected_seed_level=None).build(
        [metric("A", 10), metric("B", 20), metric("C", 30), metric("D", 40)]
    )


def incumbent_for(problem: GlobalSearchProblem) -> list[Team]:
    midpoint = problem.player_count // 2
    return [
        Team(1, [value.player for value in problem.players[:midpoint]]),
        Team(2, [value.player for value in problem.players[midpoint:]]),
    ]


def config(**overrides) -> GlobalOptimizationConfig:
    values = {
        "maximum_nodes": None,
        "maximum_evaluations": None,
        "maximum_elapsed_seconds": None,
        "score_tolerance": 1e-6,
        "minimum_improvement": 1e-6,
    }
    values.update(overrides)
    return GlobalOptimizationConfig(**values)


def test_constructor_rejects_invalid_collaborators():
    with pytest.raises(ValueError):
        GlobalOptimizer(None, config(), GlobalBoundCalculator())
    with pytest.raises(TypeError):
        GlobalOptimizer(object(), object(), GlobalBoundCalculator())
    with pytest.raises(TypeError):
        GlobalOptimizer(object(), config(), object())


@pytest.mark.parametrize("problem_value", [None, object()])
def test_optimize_requires_global_search_problem(problem_value):
    optimizer = GlobalOptimizer(object(), config(), GlobalBoundCalculator())

    with pytest.raises(TypeError):
        optimizer.optimize(problem_value, [Team(1, [])])


@pytest.mark.parametrize("incumbent", [None, [], [object()]])
def test_optimize_rejects_invalid_incumbent_sequence(incumbent):
    optimizer = GlobalOptimizer(object(), config(), GlobalBoundCalculator())

    with pytest.raises((ValueError, TypeError)):
        optimizer.optimize(complete_problem(), incumbent)


def test_incumbent_sequence_is_shallow_copied_retainining_exact_teams_and_reevaluated():
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    outer = list(incumbent)
    objective = IdentityObjective(incumbent, 50, 40)
    optimizer = GlobalOptimizer(objective, config(), ScriptedBound("upper_bound"))

    result = optimizer.optimize(problem, outer, incumbent_score=50)

    assert result.teams is not outer
    assert all(
        left is right for left, right in zip(result.teams, incumbent, strict=True)
    )
    assert objective.calls[0] is not outer
    assert len(objective.calls) == 2


def test_supplied_incumbent_score_is_consistency_assertion_with_tolerance():
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    optimizer = GlobalOptimizer(
        IdentityObjective(incumbent, 50, 40),
        config(score_tolerance=0.01),
        ScriptedBound("upper_bound"),
    )

    optimizer.optimize(problem, incumbent, incumbent_score=50.01)

    with pytest.raises(RuntimeError):
        optimizer.optimize(problem, incumbent, incumbent_score=50.011)


@pytest.mark.parametrize(
    ("candidate_score", "replaced"),
    [(50, False), (50.05, False), (50.1, False), (50.100001, True)],
)
def test_candidate_replacement_uses_strict_maximum_threshold(candidate_score, replaced):
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    objective = IdentityObjective(incumbent, 50, candidate_score)
    optimizer = GlobalOptimizer(
        objective,
        config(score_tolerance=0.01, minimum_improvement=0.1),
        ScriptedBound(),
    )

    result = optimizer.optimize(problem, incumbent)

    assert (result.teams[0] is not incumbent[0]) is replaced
    assert result.score == pytest.approx(candidate_score if replaced else 50)


def test_incumbent_only_result_is_new_and_retains_incumbent_references_and_search_metadata():
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    optimizer = GlobalOptimizer(
        IdentityObjective(incumbent, 50, 40), config(), ScriptedBound("upper_bound")
    )

    result = optimizer.optimize(problem, incumbent)

    assert isinstance(result, GlobalOptimizationResult)
    assert all(
        left is right for left, right in zip(result.teams, incumbent, strict=True)
    )
    assert result.score == result.initial_incumbent_score == 50
    assert result.improvement == 0
    assert result.incumbent_improved is False
    assert result.nodes_visited == result.pruned_nodes == result.bound_prunes == 1
    assert result.stop_reason == "SEARCH_EXHAUSTED"
    assert result.optimality_proven is True


def test_qualifying_generated_solution_uses_fresh_teams_exact_players_and_capacities():
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    optimizer = GlobalOptimizer(
        IdentityObjective(incumbent, 10, 90), config(), ScriptedBound()
    )

    result = optimizer.optimize(problem, incumbent)

    assert all(
        all(team is not incumbent_team for incumbent_team in incumbent)
        for team in result.teams
    )
    assert tuple(len(team.players) for team in result.teams) == (1, 1)
    assert {id(player) for team in result.teams for player in team.players} == {
        id(value.player) for value in problem.players
    }
    assert (
        len({id(player) for team in result.teams for player in team.players})
        == problem.player_count
    )


@pytest.mark.parametrize(
    ("reason", "counter"),
    [
        ("capacity_impossible", "capacity_prunes"),
        ("seed_impossible", "seed_prunes"),
        ("upper_bound", "bound_prunes"),
    ],
)
def test_bound_pruning_counts_visited_node_and_specific_reason(reason, counter):
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    result = GlobalOptimizer(
        IdentityObjective(incumbent, 50, 40), config(), ScriptedBound(reason)
    ).optimize(problem, incumbent)

    assert result.nodes_visited == 1
    assert result.pruned_nodes == 1
    assert getattr(result, counter) == 1
    assert sum((result.capacity_prunes, result.seed_prunes, result.bound_prunes)) == 1


def test_node_limit_is_hard_and_reports_node_limit():
    problem = branching_problem()
    incumbent = incumbent_for(problem)
    result = GlobalOptimizer(
        IdentityObjective(incumbent, 0, 50), config(maximum_nodes=1), ScriptedBound()
    ).optimize(problem, incumbent)

    assert result.nodes_visited == 1
    assert result.stopped_by_limit is True
    assert result.stop_reason == "NODE_LIMIT"
    assert result.optimality_proven is False


def test_evaluation_limit_is_hard_and_excludes_incumbent_and_final_verification():
    problem = branching_problem()
    incumbent = incumbent_for(problem)
    objective = IdentityObjective(incumbent, 0, 50)
    result = GlobalOptimizer(
        objective, config(maximum_evaluations=1), ScriptedBound()
    ).optimize(problem, incumbent)

    assert result.complete_solutions_evaluated == 1
    assert result.stop_reason == "EVALUATION_LIMIT"
    assert result.optimality_proven is False
    assert len(objective.calls) == 3


def test_time_limit_is_checked_at_operation_boundary(monkeypatch):
    import optimizer.global_search.global_optimizer as module

    clock = iter((0.0, 2.0, 2.0))
    monkeypatch.setattr(module, "perf_counter", lambda: next(clock))
    problem = branching_problem()
    incumbent = incumbent_for(problem)
    result = GlobalOptimizer(
        IdentityObjective(incumbent, 0, 50),
        config(maximum_elapsed_seconds=1),
        ScriptedBound(),
    ).optimize(problem, incumbent)

    assert result.nodes_visited == 0
    assert result.stop_reason == "TIME_LIMIT"
    assert result.stopped_by_limit is True


def test_simultaneous_node_and_evaluation_limits_prioritize_node():
    problem = branching_problem()
    optimizer = GlobalOptimizer(
        object(),
        config(maximum_nodes=1, maximum_evaluations=1),
        ScriptedBound(),
    )
    optimizer._reset(problem)
    optimizer._nodes_visited = 1
    optimizer._complete_evaluations = 1

    assert optimizer._limit_reached() is True
    assert optimizer.stop_reason == "NODE_LIMIT"


def test_exhaustive_completion_reports_search_exhausted_and_current_optimality_flag():
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    result = GlobalOptimizer(
        IdentityObjective(incumbent, 10, 90), config(), ScriptedBound()
    ).optimize(problem, incumbent)

    assert result.stop_reason == "SEARCH_EXHAUSTED"
    assert result.stopped_by_limit is False
    assert result.optimality_proven is True


def test_final_selected_state_is_reevaluated_and_inconsistency_raises():
    optimizer = GlobalOptimizer(
        SequenceObjective((10, 20, 21)), config(), ScriptedBound()
    )

    with pytest.raises(RuntimeError):
        optimizer.optimize(complete_problem(), incumbent_for(complete_problem()))


def test_malformed_objective_result_and_objective_failure_propagate():
    class Malformed:
        pass

    problem = complete_problem()
    incumbent = incumbent_for(problem)
    with pytest.raises(AttributeError):
        GlobalOptimizer(
            SequenceObjective((Malformed(),)), config(), ScriptedBound()
        ).optimize(problem, incumbent)
    with pytest.raises(LookupError):
        GlobalOptimizer(
            SequenceObjective((LookupError("objective failed"),)),
            config(),
            ScriptedBound(),
        ).optimize(problem, incumbent)


def test_bound_failure_propagates():
    problem = complete_problem()
    incumbent = incumbent_for(problem)
    optimizer = GlobalOptimizer(
        IdentityObjective(incumbent, 10, 20),
        config(),
        ScriptedBound(failure=ArithmeticError("bound failed")),
    )

    with pytest.raises(ArithmeticError):
        optimizer.optimize(problem, incumbent)


def logical_composition(teams) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(tuple(sorted(player.nick for player in team.players)) for team in teams)
    )


def test_repeated_deterministic_runs_have_identical_non_timing_results():
    problem = branching_problem()
    incumbent = incumbent_for(problem)

    def execute():
        objective = ObjectiveEngine([PowerOnlyRestriction()])
        return GlobalOptimizer(
            objective,
            config(),
            GlobalBoundCalculator(
                power_weight=1,
                elo_balance_weight=0,
                elo_spread_weight=0,
                kd_weight=0,
                team_size_weight=0,
                seed_weight=0,
            ),
        ).optimize(problem, incumbent)

    first = execute()
    second = execute()

    assert logical_composition(first.teams) == logical_composition(second.teams)
    assert first.score == second.score
    assert first.stop_reason == second.stop_reason
    assert first.nodes_visited == second.nodes_visited
    assert first.complete_solutions_evaluated == second.complete_solutions_evaluated
    assert first.pruned_nodes == second.pruned_nodes
    assert first.bound_prunes == second.bound_prunes


def test_bruteforce_verified_real_search_exhaustion_finds_true_optimum():
    values = [
        metric("Seed A", 10, seed=1),
        metric("Seed B", 40, seed=1),
        metric("Low", 20),
        metric("High", 30),
    ]
    problem = GlobalRootBuilder(2, 2, protected_seed_level=1).build(values)
    objective = ObjectiveEngine([PowerOnlyRestriction()])
    players = [value.player for value in values]
    feasible: list[list[Team]] = []
    for selected_indices in combinations(range(4), 2):
        first_indices = set(selected_indices)
        groups = (
            [players[index] for index in range(4) if index in first_indices],
            [players[index] for index in range(4) if index not in first_indices],
        )
        if all(sum(player.seed == 1 for player in group) <= 1 for group in groups):
            feasible.append([Team(1, groups[0]), Team(2, groups[1])])
    brute_scores = [objective.evaluate(teams).score for teams in feasible]
    brute_best = max(brute_scores)
    incumbent = feasible[0]
    bound = GlobalBoundCalculator(
        power_weight=1,
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )

    result = GlobalOptimizer(objective, config(), bound).optimize(
        problem, incumbent, incumbent_score=objective.evaluate(incumbent).score
    )
    fresh_score = objective.evaluate(result.teams).score

    assert len(feasible) == 4
    assert result.score == pytest.approx(brute_best)
    assert fresh_score == pytest.approx(result.score)
    assert len({id(player) for team in result.teams for player in team.players}) == 4
    assert {id(player) for team in result.teams for player in team.players} == {
        id(player) for player in players
    }
    assert tuple(len(team.players) for team in result.teams) == (2, 2)
    assert all(
        sum(player.seed == 1 for player in team.players) <= 1 for team in result.teams
    )
    assert result.stop_reason == "SEARCH_EXHAUSTED"
    assert result.optimality_proven is True
