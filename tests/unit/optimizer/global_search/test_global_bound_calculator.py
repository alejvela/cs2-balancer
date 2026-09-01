from __future__ import annotations

from itertools import product

import pytest

from models.player import Player
from optimizer.global_search.global_bound_calculator import GlobalBoundCalculator
from optimizer.global_search.global_search_problem import GlobalSearchProblem
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
)


class CapacityImpossibleState(GlobalSearchState):
    def validate_capacity_feasibility(self, total_player_count, team_size) -> bool:
        return False


def metrics(name: str, power: float, *, seed: int | None = None):
    return GlobalPlayerMetrics(Player(name), power, power * 10, 1, seed)


def problem(
    powers: tuple[float, ...] = (10, 20, 30, 40),
    *,
    root: GlobalSearchState | None = None,
    protected_seed_level: int | None = None,
) -> GlobalSearchProblem:
    players = tuple(
        metrics(chr(65 + index), power) for index, power in enumerate(powers)
    )
    return GlobalSearchProblem(
        players,
        root or GlobalSearchState.empty(2),
        number_of_teams=2,
        team_size=2,
        protected_seed_level=protected_seed_level,
    )


def power_score(groups: tuple[tuple[float, ...], ...]) -> float:
    averages = [sum(group) / len(group) for group in groups]
    global_average = sum(sum(group) for group in groups) / sum(map(len, groups))
    if global_average <= 0:
        return 100 if max(averages) - min(averages) <= 0 else 0
    return max(0.0, 100 * (1 - (max(averages) - min(averages)) / global_average))


def descendant_scores(
    value: GlobalSearchProblem, state: GlobalSearchState
) -> list[float]:
    remaining_indices = range(state.next_player_index, value.player_count)
    scores = []
    for destinations in product(
        range(value.number_of_teams), repeat=len(tuple(remaining_indices))
    ):
        groups = [
            [value.players[index].power for index in team.player_indices]
            for team in state.teams
        ]
        for player_index, team_index in zip(
            remaining_indices, destinations, strict=True
        ):
            groups[team_index].append(value.players[player_index].power)
        if all(len(group) == value.team_size for group in groups):
            scores.append(power_score(tuple(tuple(group) for group in groups)))
    return scores


def test_capacity_infeasibility_returns_capacity_prune():
    root = CapacityImpossibleState.empty(2)
    value = problem(root=root)

    result = GlobalBoundCalculator().evaluate(value, root, incumbent_score=0)

    assert result.feasible is False
    assert result.prune is True
    assert result.reason == "capacity_impossible"
    assert result.capacity_feasible is False


def test_remaining_protected_seeds_without_slots_returns_seed_prune():
    first = metrics("Placed A", 10, seed=1)
    second = metrics("Placed B", 20, seed=1)
    state = GlobalSearchState.empty(2)
    state = state.assign_next_player(0, first, 2, 1, 1)
    state = state.assign_next_player(1, second, 2, 1, 1)
    players = (
        metrics("A", 10),
        metrics("B", 20),
        metrics("Seed C", 30, seed=1),
        metrics("Seed D", 40, seed=1),
    )
    value = GlobalSearchProblem(players, state, 2, 2, 1, 1)

    result = GlobalBoundCalculator().evaluate(value, state, incumbent_score=0)

    assert result.feasible is False
    assert result.prune is True
    assert result.reason == "seed_impossible"
    assert result.seed_feasible is False


def test_power_intervals_are_optimistic_reachable_ranges():
    value = problem()
    state = value.root_state.assign_next_player(0, value.players[0], 2)

    intervals = GlobalBoundCalculator().power_intervals(value, state)

    assert intervals[0].minimum_total == 30
    assert intervals[0].maximum_total == 50
    assert intervals[1].minimum_total == 50
    assert intervals[1].maximum_total == 70


def test_elo_and_kd_bounds_remain_conservative_at_one_hundred():
    result = GlobalBoundCalculator().evaluate(problem(), GlobalSearchState.empty(2), 0)

    assert result.elo_upper_bound == 100
    assert result.kd_upper_bound == 100


def test_weighted_combined_bound_uses_component_weights():
    value = GlobalSearchProblem(
        (metrics("A", 0), metrics("B", 100)),
        GlobalSearchState.empty(2),
        2,
        1,
        protected_seed_level=None,
    )
    state = value.root_state.assign_next_player(0, value.players[0], 1)
    state = state.assign_next_player(1, value.players[1], 1)
    calculator = GlobalBoundCalculator(
        power_weight=1,
        elo_balance_weight=1,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )

    result = calculator.evaluate(value, state, incumbent_score=0)

    assert result.power_upper_bound == 0
    assert result.upper_bound == 50


@pytest.mark.parametrize(
    ("incumbent", "expected_prune"),
    [(99.999999, True), (99.999998, False)],
)
def test_upper_bound_prune_uses_inclusive_tolerance_boundary(incumbent, expected_prune):
    value = problem((10, 10, 10, 10))
    calculator = GlobalBoundCalculator(score_tolerance=1e-6)

    result = calculator.evaluate(value, value.root_state, incumbent)

    assert result.upper_bound == 100
    assert result.prune is expected_prune


def test_bound_dominates_every_bruteforce_descendant_for_compatible_power_objective():
    value = problem()
    state = value.root_state.assign_next_player(0, value.players[0], 2)
    calculator = GlobalBoundCalculator(
        power_weight=1,
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )

    actual_scores = descendant_scores(value, state)
    result = calculator.evaluate(value, state, incumbent_score=0)

    assert actual_scores
    assert result.upper_bound >= max(actual_scores)


def test_branch_with_known_better_completion_is_not_bound_pruned():
    value = problem()
    state = value.root_state.assign_next_player(0, value.players[0], 2)
    calculator = GlobalBoundCalculator(
        power_weight=1,
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )
    best_descendant = max(descendant_scores(value, state))

    result = calculator.evaluate(value, state, incumbent_score=best_descendant - 1)

    assert result.prune is False
    assert result.upper_bound >= best_descendant
