from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from models.player import Player
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from objective.objective_result import ObjectiveResult
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.local_optimizer import LocalOptimizer
from optimizer.modes.stable_optimization_config import StableOptimizationConfig
from optimizer.neighborhoods.swap_neighborhood import SwapNeighborhood
from optimizer.optimization_history import OptimizationHistory
from optimizer.optimization_phase import OptimizationPhase
from optimizer.optimization_pipeline import OptimizationPipeline
from optimizer.optimization_result import OptimizationResult
from optimizer.stable.deterministic_restart_generator import (
    DeterministicRestartGenerator,
)
from optimizer.stable.solution_selector import SolutionSelector
from optimizer.stable.solution_signature import SolutionSignature
from optimizer.stable.stable_optimizer import StableOptimizationRun, StableOptimizer
from optimizer.strategies.exhaustive_strategy import ExhaustiveStrategy


class ScriptedLocalOptimizer(LocalOptimizer):
    def __init__(
        self, handlers: Sequence[Callable[[Sequence[Team]], OptimizationResult]]
    ) -> None:
        self.handlers = list(handlers)
        self.calls: list[Sequence[Team]] = []

    def optimize(self, teams: Sequence[Team]) -> OptimizationResult:
        self.calls.append(teams)
        if not self.handlers:
            raise AssertionError("unexpected local optimization")
        return self.handlers.pop(0)(teams)


class RecordingFactory:
    def __init__(self, groupings: Sequence[tuple[tuple[str, ...], ...]]) -> None:
        self.groupings = list(groupings)
        self.calls: list[tuple[Sequence[Team], int, int]] = []

    def __call__(self, initial_teams, restart_index, seed) -> list[Team]:
        self.calls.append((initial_teams, restart_index, seed))
        players = {
            player.nick: player for team in initial_teams for player in team.players
        }
        grouping = self.groupings[restart_index]
        return [
            Team(index, [players[name] for name in group])
            for index, group in enumerate(grouping, 1)
        ]


class FirstPlayerRestriction(Restriction):
    @property
    def name(self) -> str:
        return "First player"

    def evaluate(self, teams) -> RestrictionResult:
        score = 90 if teams[0].players[0].nick == "target" else 10
        return RestrictionResult(self.name, score)


GROUP_A = (("A", "B"), ("C", "D"))
GROUP_B = (("A", "C"), ("B", "D"))
GROUP_C = (("A", "D"), ("B", "C"))


def initial_teams() -> list[Team]:
    return [Team(1, [Player("A"), Player("B")]), Team(2, [Player("C"), Player("D")])]


def config(**overrides) -> StableOptimizationConfig:
    values = {
        "target_score": 99,
        "maximum_restarts": 3,
        "minimum_restarts": 3,
        "convergence_patience": 3,
        "minimum_unique_solutions": 0,
        "target_confirmation_restarts": 3,
        "base_seed": 700,
        "stop_on_perfect_score": False,
    }
    values.update(overrides)
    return StableOptimizationConfig(**values)


def optimization_result(
    teams: Sequence[Team], score: float, *, penalty: float = 0
) -> OptimizationResult:
    objective = ObjectiveResult()
    objective.add_result(RestrictionResult("Quality", score, penalty=penalty))
    objective.score = score
    return OptimizationResult(teams, objective, OptimizationHistory())


def handler(score: float, *, penalty: float = 0):
    return lambda teams: optimization_result(teams, score, penalty=penalty)


def test_constructor_rejects_invalid_required_collaborators():
    local = ScriptedLocalOptimizer([])
    with pytest.raises(ValueError):
        StableOptimizer(None, lambda teams, index, seed: teams)
    with pytest.raises(TypeError):
        StableOptimizer(object(), lambda teams, index, seed: teams)
    with pytest.raises(ValueError):
        StableOptimizer(local, None)
    with pytest.raises(TypeError):
        StableOptimizer(local, object())


def test_constructor_defaults_config_selector_and_initial_run_state():
    local = ScriptedLocalOptimizer([])

    def factory(teams, index, seed):
        return teams

    optimizer = StableOptimizer(local, factory)

    assert optimizer.local_optimizer is local
    assert optimizer.restart_factory is factory
    assert optimizer.config == StableOptimizationConfig.balanced()
    assert optimizer.selector.config is optimizer.config
    assert optimizer.last_run is None
    with pytest.raises(RuntimeError):
        optimizer.require_last_run()


def test_constructor_validates_selector_type_and_equivalent_configuration():
    local = ScriptedLocalOptimizer([])
    selected_config = config()
    with pytest.raises(TypeError):
        StableOptimizer(
            local, lambda teams, index, seed: teams, selected_config, object()
        )
    with pytest.raises(ValueError):
        StableOptimizer(
            local,
            lambda teams, index, seed: teams,
            selected_config,
            SolutionSelector(config(base_seed=701)),
        )

    selector = SolutionSelector(config())
    optimizer = StableOptimizer(
        local, lambda teams, index, seed: teams, selected_config, selector
    )
    assert optimizer.config is selected_config
    assert optimizer.selector is selector


@pytest.mark.parametrize("value", [None, [], [None], [object()]])
def test_optimize_rejects_invalid_team_input(value):
    optimizer = StableOptimizer(
        ScriptedLocalOptimizer([]), lambda teams, index, seed: teams, config()
    )

    with pytest.raises((ValueError, TypeError)):
        optimizer.optimize(value)


def test_restart_indices_seeds_calls_and_hard_cap_are_deterministic():
    teams = initial_teams()
    outer = list(teams)
    factory = RecordingFactory([GROUP_A, GROUP_B, GROUP_C])
    local = ScriptedLocalOptimizer([handler(50), handler(60), handler(55)])
    optimizer = StableOptimizer(local, factory, config(maximum_restarts=3))

    run = optimizer.optimize_with_details(outer)

    assert [(index, seed) for _, index, seed in factory.calls] == [
        (0, 700),
        (1, 701),
        (2, 702),
    ]
    assert factory.calls[0][0] is not outer
    assert len(factory.calls) == len(local.calls) == run.completed_restarts == 3
    assert run.result.score == 60


def test_optimize_returns_exact_selected_result_and_details_update_last_run():
    factory = RecordingFactory([GROUP_A])
    created: list[OptimizationResult] = []

    def build(teams):
        value = optimization_result(teams, 50)
        created.append(value)
        return value

    local = ScriptedLocalOptimizer([build])
    optimizer = StableOptimizer(
        local,
        factory,
        config(
            maximum_restarts=1,
            minimum_restarts=1,
            convergence_patience=1,
            target_confirmation_restarts=1,
        ),
    )

    selected = optimizer.optimize(initial_teams())

    assert selected is created[0]
    assert optimizer.last_run is not None
    assert optimizer.last_run.result is selected
    assert optimizer.require_last_run() is optimizer.last_run


def test_optimize_with_details_exposes_selected_result_signature_and_run_metadata():
    factory = RecordingFactory([GROUP_A, GROUP_B])
    created: list[OptimizationResult] = []

    def collecting(score):
        def build(teams):
            value = optimization_result(teams, score)
            created.append(value)
            return value

        return build

    optimizer = StableOptimizer(
        ScriptedLocalOptimizer([collecting(50), collecting(70)]),
        factory,
        config(
            maximum_restarts=2,
            minimum_restarts=2,
            convergence_patience=2,
            target_confirmation_restarts=2,
        ),
    )

    run = optimizer.optimize_with_details(initial_teams())

    assert isinstance(run, StableOptimizationRun)
    assert run.result is created[1]
    assert run.signature == SolutionSignature.from_teams(run.result.teams)
    assert run.completed_restarts == 2
    assert run.unique_solutions == 2
    assert run.selection_changes == 2
    assert run.quality_improvements == 2
    assert run.best_restart_index == 1
    assert run.stop_reason == run.convergence.stop_reason
    assert optimizer.last_run is run
    assert optimizer.require_last_run() is run


@pytest.mark.parametrize("failure_source", ["factory", "local"])
def test_restart_or_local_failure_propagates_without_successful_last_run(
    failure_source,
):
    def failing_factory(teams, index, seed):
        raise LookupError("factory failed")

    def failing_local(teams):
        raise ArithmeticError("local failed")

    factory = (
        failing_factory if failure_source == "factory" else RecordingFactory([GROUP_A])
    )
    handlers = [failing_local] if failure_source == "local" else []
    optimizer = StableOptimizer(ScriptedLocalOptimizer(handlers), factory, config())

    with pytest.raises((LookupError, ArithmeticError)):
        optimizer.optimize(initial_teams())

    assert optimizer.last_run is None


def test_invalid_local_optimizer_return_is_rejected():
    local = ScriptedLocalOptimizer([lambda teams: None])
    optimizer = StableOptimizer(local, RecordingFactory([GROUP_A]), config())

    with pytest.raises(RuntimeError):
        optimizer.optimize(initial_teams())


def test_factory_must_preserve_team_count_and_logical_player_pool():
    source = initial_teams()

    def changed_count(teams, index, seed):
        return [Team(1, [player for team in teams for player in team.players])]

    def changed_pool(teams, index, seed):
        return [
            Team(1, [Player("X"), Player("B")]),
            Team(2, [Player("C"), Player("D")]),
        ]

    for factory in (changed_count, changed_pool):
        optimizer = StableOptimizer(
            ScriptedLocalOptimizer([handler(50)]), factory, config()
        )
        with pytest.raises(RuntimeError):
            optimizer.optimize(source)


def test_optimized_result_must_preserve_logical_player_pool():
    def corrupt_result(teams):
        value = [
            Team(1, [Player("X"), Player("B")]),
            Team(2, [Player("C"), Player("D")]),
        ]
        return optimization_result(value, 50)

    optimizer = StableOptimizer(
        ScriptedLocalOptimizer([corrupt_result]), RecordingFactory([GROUP_A]), config()
    )

    with pytest.raises(RuntimeError):
        optimizer.optimize(initial_teams())


def test_duplicate_stable_player_identity_is_rejected():
    teams = [Team(1, [Player("Same")]), Team(2, [Player("same")])]
    optimizer = StableOptimizer(
        ScriptedLocalOptimizer([]), lambda value, index, seed: value, config()
    )

    with pytest.raises(ValueError):
        optimizer.optimize(teams)


def test_equal_quality_canonical_replacement_changes_selection_not_quality():
    ordered = sorted(
        (GROUP_A, GROUP_B),
        key=lambda group: SolutionSignature.from_teams(
            [
                Team(index, [Player(name) for name in names])
                for index, names in enumerate(group, 1)
            ]
        ),
    )
    factory = RecordingFactory([ordered[1], ordered[0]])
    optimizer = StableOptimizer(
        ScriptedLocalOptimizer([handler(50), handler(50)]),
        factory,
        config(
            maximum_restarts=2,
            minimum_restarts=2,
            convergence_patience=2,
            target_confirmation_restarts=2,
        ),
    )

    run = optimizer.optimize_with_details(initial_teams())

    assert run.signature == SolutionSignature.from_teams(run.result.teams)
    assert run.selection_changes == 2
    assert run.quality_improvements == 1
    assert run.best_restart_index == 0
    assert run.convergence.restarts_without_improvement == 1


def test_duplicate_signature_and_distinct_equal_score_grouping_update_uniqueness():
    factory = RecordingFactory([GROUP_A, GROUP_A, GROUP_B])
    optimizer = StableOptimizer(
        ScriptedLocalOptimizer([handler(50), handler(50), handler(50)]),
        factory,
        config(),
    )

    run = optimizer.optimize_with_details(initial_teams())

    assert run.completed_restarts == 3
    assert run.unique_solutions == 2
    assert run.convergence.restarts_without_improvement == 2


def test_same_deterministic_setup_reproduces_non_timing_selection_state():
    def execute():
        factory = RecordingFactory([GROUP_A, GROUP_B, GROUP_A])
        optimizer = StableOptimizer(
            ScriptedLocalOptimizer([handler(50), handler(60), handler(50)]),
            factory,
            config(),
        )
        run = optimizer.optimize_with_details(initial_teams())
        return run, [(index, seed) for _, index, seed in factory.calls]

    first, first_calls = execute()
    second, second_calls = execute()

    assert first_calls == second_calls
    assert first.signature == second.signature
    assert first.completed_restarts == second.completed_restarts
    assert first.unique_solutions == second.unique_solutions
    assert first.selection_changes == second.selection_changes
    assert first.quality_improvements == second.quality_improvements
    assert (
        first.convergence.restarts_without_improvement
        == second.convergence.restarts_without_improvement
    )
    assert first.stop_reason == second.stop_reason


def test_restart_zero_clones_teams_and_lists_but_retains_exact_players():
    teams = initial_teams()
    before = tuple(tuple(team.players) for team in teams)

    restarted = DeterministicRestartGenerator()(teams, 0, 123)

    assert all(new is not old for new, old in zip(restarted, teams, strict=True))
    assert all(
        new.players is not old.players
        for new, old in zip(restarted, teams, strict=True)
    )
    assert all(
        new_player is old_player
        for new, old in zip(restarted, teams, strict=True)
        for new_player, old_player in zip(new.players, old.players, strict=True)
    )
    assert tuple(tuple(team.players) for team in teams) == before


def test_later_restart_is_reproducible_for_same_input_index_and_seed():
    teams = initial_teams()
    generator = DeterministicRestartGenerator(separated_seed_level=None)

    first = generator(teams, 2, 987)
    second = generator(teams, 2, 987)

    assert SolutionSignature.from_teams(first) == SolutionSignature.from_teams(second)


def test_real_production_style_integration_matches_fresh_objective_evaluation():
    low = Player("low")
    target = Player("target")
    teams = [Team(1, [low]), Team(2, [target])]
    before = tuple(tuple(team.players) for team in teams)
    objective = ObjectiveEngine([FirstPlayerRestriction()])
    local = LocalOptimizer(
        MoveEvaluator(objective),
        OptimizationPipeline(
            [
                OptimizationPhase(
                    "swap",
                    SwapNeighborhood(),
                    ExhaustiveStrategy(minimum_improvement=0.01),
                    max_iterations=2,
                )
            ]
        ),
    )
    optimizer = StableOptimizer(
        local,
        DeterministicRestartGenerator(separated_seed_level=None),
        config(
            maximum_restarts=2,
            minimum_restarts=2,
            convergence_patience=2,
            target_confirmation_restarts=2,
        ),
    )

    run = optimizer.optimize_with_details(teams)
    fresh_score = objective.evaluate(run.result.teams).score

    assert fresh_score == run.result.score == 90
    assert {id(player) for team in run.result.teams for player in team.players} == {
        id(low),
        id(target),
    }
    assert tuple(len(team.players) for team in run.result.teams) == (1, 1)
    assert tuple(tuple(team.players) for team in teams) == before
    assert all(
        result_team is not input_team
        for result_team, input_team in zip(run.result.teams, teams, strict=True)
    )
