from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from models.player import Player
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
)


def metrics(name: str, *, seed: int | None = None) -> GlobalPlayerMetrics:
    return GlobalPlayerMetrics(Player(name), power=10, elo=1000, kd=1, seed=seed)


def test_assignment_returns_new_state_and_leaves_parent_unchanged():
    root = GlobalSearchState.empty(2)

    child = root.assign_next_player(0, metrics("A"), team_size=2)

    assert child is not root
    assert root.assigned_count == root.next_player_index == 0
    assert root.team_sizes == (0, 0)
    assert child.assigned_count == child.next_player_index == 1
    assert child.team_sizes == (1, 0)
    assert child.teams[0].player_indices == (0,)


def test_state_and_team_state_are_frozen():
    state = GlobalSearchState.empty(2)

    with pytest.raises(FrozenInstanceError):
        state.assigned_count = 1
    with pytest.raises(FrozenInstanceError):
        state.teams[0].player_count = 1


def test_sequential_assignments_store_sequential_player_indices():
    state = GlobalSearchState.empty(2)
    state = state.assign_next_player(1, metrics("A"), team_size=2)
    state = state.assign_next_player(0, metrics("B"), team_size=2)

    assert state.next_player_index == state.assigned_count == 2
    assert state.teams[0].player_indices == (1,)
    assert state.teams[1].player_indices == (0,)


def test_assignment_rejects_full_team():
    state = GlobalSearchState.empty(2).assign_next_player(0, metrics("A"), team_size=1)

    with pytest.raises(ValueError):
        state.assign_next_player(0, metrics("B"), team_size=1)


def test_assignment_rejects_second_protected_seed_in_team():
    state = GlobalSearchState.empty(2).assign_next_player(
        0,
        metrics("Seed A", seed=1),
        team_size=2,
        protected_seed_level=1,
        maximum_protected_seeds_per_team=1,
    )

    with pytest.raises(ValueError):
        state.assign_next_player(
            0,
            metrics("Seed B", seed=1),
            team_size=2,
            protected_seed_level=1,
            maximum_protected_seeds_per_team=1,
        )


def test_completion_and_remaining_player_semantics():
    state = GlobalSearchState.empty(1)
    assert state.is_complete(1) is False
    assert state.remaining_players(1) == 1

    complete = state.assign_next_player(0, metrics("A"), team_size=1)

    assert complete.is_complete(1) is True
    assert complete.remaining_players(1) == 0


def test_capacity_feasibility_compares_remaining_slots_and_players():
    state = GlobalSearchState.empty(2).assign_next_player(0, metrics("A"), team_size=2)

    assert state.total_remaining_capacity(2) == 3
    assert state.validate_capacity_feasibility(4, 2) is True
    assert state.validate_capacity_feasibility(5, 2) is False


def test_empty_team_symmetry_keeps_only_first_equivalent_empty_team():
    root = GlobalSearchState.empty(3)
    assert root.canonical_available_team_indices(2) == (0,)

    child = root.assign_next_player(0, metrics("A"), team_size=2)

    assert child.canonical_available_team_indices(2) == (0, 1)
