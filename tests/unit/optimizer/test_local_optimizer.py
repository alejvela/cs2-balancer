from __future__ import annotations

from collections.abc import Sequence

import pytest

from models.player import Player
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.local_optimizer import LocalOptimizer
from optimizer.moves.move import Move
from optimizer.moves.swap_move import SwapMove
from optimizer.neighborhoods.swap_neighborhood import SwapNeighborhood
from optimizer.optimization_phase import OptimizationPhase
from optimizer.optimization_pipeline import OptimizationPipeline
from optimizer.strategies.exhaustive_strategy import ExhaustiveStrategy
from optimizer.strategies.search_result import SearchResult
from optimizer.strategies.search_strategy import SearchStrategy


class FirstTeamPlayerRestriction(Restriction):
    def __init__(self, scores: dict[str, float]) -> None:
        super().__init__()
        self.scores = scores

    @property
    def name(self) -> str:
        return "First team player"

    def evaluate(self, teams) -> RestrictionResult:
        nick = teams[0].players[0].nick
        return RestrictionResult(name=self.name, score=self.scores[nick])


class ScriptedStrategy(SearchStrategy):
    def __init__(self, results: Sequence[SearchResult]) -> None:
        self.results = list(results)
        self.searches = 0
        self.resets = 0

    @property
    def name(self) -> str:
        return "Scripted"

    def reset(self) -> None:
        self.resets += 1

    def search(self, neighborhood, teams, evaluator, current_score) -> SearchResult:
        self.searches += 1
        if self.results:
            return self.results.pop(0)
        return SearchResult.no_move(current_score, evaluations=3, elapsed=0.25)


class CorruptMove(Move):
    def __init__(self, teams: Sequence[Team]) -> None:
        self.teams = teams

    def apply(self, teams) -> None:
        self.teams[0].players.append(self.teams[1].players[0])

    def undo(self, teams) -> None:
        self.teams[0].players.pop()


class MutateThenFailMove(Move):
    def __init__(self, teams: Sequence[Team]) -> None:
        self.teams = teams

    def apply(self, teams) -> None:
        self.teams[0].players[0], self.teams[1].players[0] = (
            self.teams[1].players[0],
            self.teams[0].players[0],
        )
        raise LookupError("commit failed")

    def undo(self, teams) -> None:
        raise AssertionError("undo is not used for a failed commit")


class FailCommittedCurrentEvaluator:
    def __init__(self, delegate: MoveEvaluator) -> None:
        self.delegate = delegate
        self.current_calls = 0

    def current(self, teams):
        self.current_calls += 1
        if self.current_calls == 2:
            raise ArithmeticError("committed evaluation failed")
        return self.delegate.current(teams)

    def evaluate(self, move, teams):
        return self.delegate.evaluate(move, teams)


def make_teams(*names: str) -> list[Team]:
    return [Team(index, [Player(name)]) for index, name in enumerate(names, 1)]


def identity_snapshot(teams: Sequence[Team]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(id(player) for player in team.players) for team in teams)


def evaluator_for(scores: dict[str, float]) -> tuple[MoveEvaluator, ObjectiveEngine]:
    objective = ObjectiveEngine([FirstTeamPlayerRestriction(scores)])
    return MoveEvaluator(objective), objective


def pipeline_for(
    strategy: SearchStrategy,
    *,
    max_iterations: int = 1,
    enabled: bool = True,
    stop_when_no_move: bool = True,
    name: str = "Test phase",
) -> OptimizationPipeline:
    return OptimizationPipeline(
        [
            OptimizationPhase(
                name=name,
                neighborhood=SwapNeighborhood(),
                strategy=strategy,
                max_iterations=max_iterations,
                enabled=enabled,
                stop_when_no_move=stop_when_no_move,
            )
        ]
    )


def optimizer_with_strategy(
    strategy: SearchStrategy,
    scores: dict[str, float],
    **phase_options,
) -> tuple[LocalOptimizer, ObjectiveEngine]:
    evaluator, objective = evaluator_for(scores)
    return LocalOptimizer(evaluator, pipeline_for(strategy, **phase_options)), objective


@pytest.mark.parametrize(
    ("evaluator", "pipeline"),
    [
        (None, OptimizationPipeline()),
        (object(), None),
        (object(), OptimizationPipeline()),
    ],
)
def test_constructor_rejects_missing_collaborators_and_empty_pipeline(
    evaluator, pipeline
):
    with pytest.raises(ValueError):
        LocalOptimizer(evaluator, pipeline)


def test_constructor_exposes_exact_collaborator_references():
    evaluator, _ = evaluator_for({"A": 50})
    pipeline = pipeline_for(ScriptedStrategy([]))
    optimizer = LocalOptimizer(evaluator, pipeline)

    assert optimizer.evaluator is evaluator
    assert optimizer.pipeline is pipeline


@pytest.mark.parametrize("teams", [None, [], [None], [object()]])
def test_optimize_rejects_invalid_team_inputs(teams):
    optimizer, _ = optimizer_with_strategy(ScriptedStrategy([]), {"A": 50})

    with pytest.raises((ValueError, AttributeError)):
        optimizer.optimize(teams)


def test_optimize_rejects_initially_duplicated_player_identity():
    player = Player("A")
    teams = [Team(1, [player]), Team(2, [player])]
    optimizer, _ = optimizer_with_strategy(ScriptedStrategy([]), {"A": 50})

    with pytest.raises(ValueError):
        optimizer.optimize(teams)


def test_no_move_preserves_identity_order_and_returns_final_current_score():
    teams = make_teams("A", "B")
    outer_sequence = list(teams)
    before = identity_snapshot(teams)
    strategy = ScriptedStrategy([])
    optimizer, objective = optimizer_with_strategy(strategy, {"A": 40, "B": 90})

    result = optimizer.optimize(outer_sequence)

    assert result.teams is not outer_sequence
    assert all(
        result_team is input_team
        for result_team, input_team in zip(result.teams, teams, strict=True)
    )
    assert identity_snapshot(result.teams) == before
    assert result.iterations == result.accepted_movements == 0
    assert result.history.is_empty
    assert result.score == objective.evaluate(teams).score == 40
    assert result.initial_score == result.final_score
    assert strategy.searches == 1


def test_fast_style_real_integration_commits_improvement_and_preserves_structure():
    teams = make_teams("low", "target")
    original_teams = tuple(teams)
    original_players = {id(player) for team in teams for player in team.players}
    evaluator, objective = evaluator_for({"low": 10, "target": 90})
    pipeline = pipeline_for(ExhaustiveStrategy(minimum_improvement=0.01))

    result = LocalOptimizer(evaluator, pipeline).optimize(teams)

    assert result.teams[0] is original_teams[0]
    assert result.teams[1] is original_teams[1]
    assert result.teams[0].players[0].nick == "target"
    assert tuple(len(team.players) for team in result.teams) == (1, 1)
    assert {
        id(player) for team in result.teams for player in team.players
    } == original_players
    assert len({id(player) for team in result.teams for player in team.players}) == 2
    assert result.score == result.final_score == result.objective_result.score
    assert result.score == objective.evaluate(result.teams).score == 90
    assert result.initial_score == 10
    assert result.improvement == 80
    assert result.iterations == result.accepted_movements == 1


def test_committed_score_reevaluation_overrides_strategy_prediction_and_populates_history():
    teams = make_teams("A", "B")
    move = SwapMove(teams[0], teams[0].players[0], teams[1], teams[1].players[0])
    predicted = SearchResult.from_move(
        move, score_before=20, score_after=99, evaluations=7, elapsed=0.125
    )
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy([predicted]), {"A": 20, "B": 70}
    )

    result = optimizer.optimize(teams)
    iteration = result.history[0]

    assert teams[0].players[0].nick == "B"
    assert iteration.score_before == 20
    assert iteration.score_after == result.final_score == 70
    assert iteration.evaluations == 7
    assert iteration.elapsed == 0.125
    assert iteration.phase == "Test phase"
    assert iteration.strategy == "Scripted"
    assert iteration.neighborhood == "SwapNeighborhood"


def test_structurally_corrupt_commit_is_detected_and_rolled_back_exactly():
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    move = CorruptMove(teams)
    result = SearchResult.from_move(move, 20, 90)
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy([result]), {"A": 20, "B": 90}
    )

    with pytest.raises(RuntimeError):
        optimizer.optimize(teams)

    assert identity_snapshot(teams) == before


def test_commit_application_failure_restores_exact_state_and_propagates():
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    move = MutateThenFailMove(teams)
    result = SearchResult.from_move(move, 20, 90)
    optimizer, _ = optimizer_with_strategy(
        ScriptedStrategy([result]), {"A": 20, "B": 90}
    )

    with pytest.raises(LookupError):
        optimizer.optimize(teams)

    assert identity_snapshot(teams) == before


def test_committed_state_evaluation_failure_restores_exact_state_and_propagates():
    teams = make_teams("A", "B")
    before = identity_snapshot(teams)
    move = SwapMove(teams[0], teams[0].players[0], teams[1], teams[1].players[0])
    strategy = ScriptedStrategy([SearchResult.from_move(move, 20, 90)])
    real_evaluator, _ = evaluator_for({"A": 20, "B": 90})
    evaluator = FailCommittedCurrentEvaluator(real_evaluator)
    optimizer = LocalOptimizer(evaluator, pipeline_for(strategy))

    with pytest.raises(ArithmeticError):
        optimizer.optimize(teams)

    assert identity_snapshot(teams) == before


def test_worse_intermediate_move_is_recorded_but_best_snapshot_is_restored():
    teams = make_teams("A", "B", "C")
    player_a, player_b, player_c = (team.players[0] for team in teams)
    improving = SwapMove(teams[0], player_a, teams[1], player_b)
    worsening = SwapMove(teams[0], player_b, teams[2], player_c)
    strategy = ScriptedStrategy(
        [
            SearchResult.from_move(improving, 40, 90),
            SearchResult.from_move(worsening, 90, 20),
        ]
    )
    optimizer, objective = optimizer_with_strategy(
        strategy,
        {"A": 40, "B": 90, "C": 20},
        max_iterations=2,
        stop_when_no_move=False,
    )

    result = optimizer.optimize(teams)

    assert [iteration.score_after for iteration in result.history] == [90, 20]
    assert result.history.non_improving_iterations == 1
    assert teams[0].players[0] is player_b
    assert teams[1].players[0] is player_a
    assert teams[2].players[0] is player_c
    assert result.final_score == objective.evaluate(teams).score == 90
    assert result.final_score + LocalOptimizer.SCORE_TOLERANCE >= result.initial_score


def test_disabled_phase_is_skipped_but_pipeline_reset_reaches_its_strategy():
    disabled = ScriptedStrategy([])
    enabled = ScriptedStrategy([])
    evaluator, _ = evaluator_for({"A": 50, "B": 60})
    pipeline = OptimizationPipeline(
        [
            OptimizationPhase("Disabled", SwapNeighborhood(), disabled, enabled=False),
            OptimizationPhase("Enabled", SwapNeighborhood(), enabled),
        ]
    )

    LocalOptimizer(evaluator, pipeline).optimize(make_teams("A", "B"))

    assert disabled.searches == 0
    assert disabled.resets == 1
    assert enabled.searches == 1
    assert enabled.resets == 2


@pytest.mark.parametrize(
    ("stop_when_no_move", "expected_searches"),
    [(True, 1), (False, 4)],
)
def test_no_move_stopping_and_max_iterations_are_respected(
    stop_when_no_move, expected_searches
):
    strategy = ScriptedStrategy([])
    optimizer, _ = optimizer_with_strategy(
        strategy,
        {"A": 50, "B": 60},
        max_iterations=4,
        stop_when_no_move=stop_when_no_move,
    )

    result = optimizer.optimize(make_teams("A", "B"))

    assert strategy.searches == expected_searches
    assert result.history.is_empty
    assert result.total_evaluations == 0
