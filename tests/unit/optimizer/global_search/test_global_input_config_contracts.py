"""SCRUM-49: truthful GLOBAL inputs, policy switches and absent incumbents."""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from models.numeric import finite_real
from models.player import Player
from models.team import Team
from optimizer.global_search.global_bound_calculator import GlobalBoundCalculator
from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.global_search.global_optimizer import GlobalOptimizer
from optimizer.global_search.global_pruning_policy import GlobalPruningPolicy
from optimizer.global_search.global_root_builder import GlobalRootBuilder
from optimizer.global_search.global_search_problem import GlobalSearchProblem
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
    GlobalTeamState,
)
from optimizer.stable.solution_signature import SolutionSignature


class RecordingObjective:
    def __init__(self, score=50):
        self.score = score
        self.calls = []

    def evaluate(self, teams):
        self.calls.append(tuple(teams))
        return self.score


def search_config(**overrides):
    values = dict(
        maximum_nodes=None,
        maximum_evaluations=None,
        maximum_elapsed_seconds=None,
        use_power_bound=False,
    )
    values.update(overrides)
    return GlobalOptimizationConfig(**values)


def make_problem(*, seeds=(), root=None):
    metrics = tuple(
        GlobalPlayerMetrics(
            Player(name, elo=power, seed=1 if index in seeds else None),
            power,
            power,
            1,
            1 if index in seeds else None,
        )
        for index, (name, power) in enumerate(
            zip("ABCD", (10, 20, 30, 40), strict=True)
        )
    )
    return GlobalSearchProblem(
        metrics,
        root or GlobalSearchState.empty(2),
        2,
        2,
        protected_seed_level=1 if seeds else None,
    )


def incumbent(problem, *, groups=((0, 1), (2, 3))):
    return [
        Team(i + 1, [problem.players[index].player for index in group])
        for i, group in enumerate(groups)
    ]


def solver(objective=None, **overrides):
    config = search_config(**overrides)
    return GlobalOptimizer(
        objective if objective is not None else RecordingObjective(),
        config,
        GlobalBoundCalculator(pruning_policy=config.pruning_policy),
    )


def test_enabled_incumbent_is_required_before_objective_or_search():
    objective = RecordingObjective()
    optimizer = solver(objective)
    with pytest.raises(ValueError, match="required"):
        optimizer.optimize(make_problem())
    assert objective.calls == []
    assert optimizer.nodes_visited == 0
    assert optimizer.best_score is None
    assert "best_score=None" in repr(optimizer)


def test_disabled_incumbent_establishes_first_valid_solution_without_fake_baseline():
    objective = RecordingObjective(score=0)
    optimizer = solver(objective, use_incumbent=False, minimum_improvement=1000)
    result = optimizer.optimize(make_problem())
    assert result.score == 0  # first complete result ignores improvement threshold
    assert result.initial_incumbent_score is None
    assert result.improvement is None
    assert result.incumbent_improved is False
    assert result.as_dict()["initial_incumbent_score"] is None
    assert result.as_dict()["improvement"] is None
    assert result.complete_solutions_evaluated > 0
    assert len(objective.calls) == result.complete_solutions_evaluated + 1
    assert result.bound_prunes == 0
    assert optimizer.best_score == 0


@pytest.mark.parametrize("data", ["teams", "score", "both"])
def test_disabled_incumbent_rejects_any_supplied_data_before_evaluation(data):
    problem = make_problem()
    objective = RecordingObjective()
    optimizer = solver(objective, use_incumbent=False)
    with pytest.raises(ValueError, match="forbidden"):
        optimizer.optimize(
            problem,
            incumbent_teams=incumbent(problem) if data != "score" else None,
            incumbent_score=50 if data != "teams" else None,
        )
    assert not objective.calls
    assert optimizer.nodes_visited == 0


@pytest.mark.parametrize(
    "corruption",
    [
        "count",
        "type",
        "size",
        "added",
        "missing",
        "substitution",
        "duplicate",
        "team_instance",
    ],
)
def test_invalid_incumbent_never_reaches_objective(corruption):
    problem = make_problem()
    teams = incumbent(problem)
    if corruption == "count":
        teams.pop()
    elif corruption == "type":
        teams[0] = object()
    elif corruption in ("size", "added"):
        teams[0].players.append(Player("extra"))
    elif corruption == "missing":
        teams[0].players.pop()
    elif corruption == "substitution":
        teams[0].players[0] = Player("replacement")
    elif corruption == "duplicate":
        teams[0].players[0] = Player("c")
    elif corruption == "team_instance":
        teams[1] = teams[0]
    objective = RecordingObjective()
    optimizer = solver(objective)
    with pytest.raises((TypeError, ValueError)):
        optimizer.optimize(problem, teams)
    assert objective.calls == []
    assert optimizer.nodes_visited == 0


def test_incumbent_accepts_fresh_logical_players_arbitrary_team_ids_and_order():
    problem = make_problem()
    teams = [Team(99, [Player("d"), Player("c")]), Team(99, [Player("b"), Player("a")])]
    objective = RecordingObjective(100)
    result = solver(objective).optimize(problem, teams)
    assert all(a is b for a, b in zip(result.teams, teams, strict=True))
    assert result.initial_incumbent_score == 100
    assert result.improvement == 0
    assert objective.calls[0] == tuple(teams)


def test_fresh_players_cannot_hide_problem_protected_seed_constraints():
    problem = make_problem(seeds=(0, 1))
    teams = [
        Team(1, [Player("A", seed=None), Player("B", seed=None)]),
        Team(2, [Player("C"), Player("D")]),
    ]
    objective = RecordingObjective()
    with pytest.raises(ValueError, match="protected seed"):
        solver(objective, use_seed_pruning=False).optimize(problem, teams)
    assert not objective.calls


def test_fresh_equivalent_protected_players_in_valid_groups_are_accepted():
    problem = make_problem(seeds=(0, 1))
    teams = [
        Team(8, [Player("A", seed=1), Player("C")]),
        Team(7, [Player("B", seed=1), Player("D")]),
    ]
    result = solver(RecordingObjective(100)).optimize(problem, teams)
    assert result.score == 100


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
def test_supplied_incumbent_score_uses_finite_numeric_policy(value):
    problem = make_problem()
    objective = RecordingObjective()
    with pytest.raises((TypeError, ValueError)):
        solver(objective).optimize(problem, incumbent(problem), value)
    assert not objective.calls


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("result_kind", ["numeric", "score", "final_score"])
def test_authoritative_scores_reject_boolean_and_nonfinite_values(value, result_kind):
    score = (
        value if result_kind == "numeric" else SimpleNamespace(**{result_kind: value})
    )
    objective = RecordingObjective(score)
    problem = make_problem()
    with pytest.raises((TypeError, ValueError)):
        solver(objective).optimize(problem, incumbent(problem))


def test_finite_supplied_incumbent_score_must_match_authoritative_evaluation():
    problem = make_problem()
    with pytest.raises(RuntimeError, match="does not match"):
        solver().optimize(problem, incumbent(problem), 51)
    result = solver().optimize(problem, incumbent(problem), 50.0000001)
    assert result.initial_incumbent_score == 50


@pytest.mark.parametrize("field", ["use_elo_bound", "deterministic", "base_seed"])
def test_removed_public_arguments_are_rejected_without_aliases(field):
    with pytest.raises(TypeError):
        GlobalOptimizationConfig(**{field: True})
    for preset in (
        GlobalOptimizationConfig.smoke_test,
        GlobalOptimizationConfig.balanced,
        GlobalOptimizationConfig.deep,
        GlobalOptimizationConfig.proof,
    ):
        config = preset()
        assert field not in config.as_dict()
        assert not hasattr(config, field)


def test_policy_is_immutable_and_optimizer_rejects_mismatched_wiring():
    policy = GlobalPruningPolicy()
    with pytest.raises(FrozenInstanceError):
        policy.use_power_bound = False
    with pytest.raises(ValueError, match="policy must match"):
        GlobalOptimizer(RecordingObjective(), search_config(), GlobalBoundCalculator())
    with pytest.raises(TypeError):
        GlobalBoundCalculator(pruning_policy=object())
    for field in ("use_capacity_pruning", "use_seed_pruning", "use_power_bound"):
        with pytest.raises(TypeError):
            GlobalPruningPolicy(**{field: 0})


def test_symmetry_switch_changes_available_branches_and_exhaustive_work(monkeypatch):
    from objective.objective_engine import ObjectiveEngine
    from objective.restrictions.team_size_restriction import TeamSizeRestriction
    objective = ObjectiveEngine([TeamSizeRestriction(expected_size=3, penalty_per_position=25)])
    problem = make_problem()
    calls = []
    original = GlobalSearchState.canonical_available_team_indices

    def canonical(state, team_size):
        indices = original(state, team_size)
        calls.append((state.depth, indices))
        return indices

    monkeypatch.setattr(
        GlobalSearchState, "canonical_available_team_indices", canonical
    )
    branch_options = []
    ordering = GlobalOptimizer._order_candidate_teams

    def record_options(optimizer, state, team_indices, player):
        branch_options.append((state.depth, team_indices))
        return ordering(optimizer, state, team_indices, player)

    monkeypatch.setattr(GlobalOptimizer, "_order_candidate_teams", record_options)
    enabled = solver(objective, use_incumbent=False).optimize(problem)
    assert branch_options[0] == (0, (0,))
    assert calls[0] == (0, (0,))
    assert calls
    calls.clear()
    branch_options.clear()
    disabled = solver(objective, use_incumbent=False, use_symmetry_breaking=False).optimize(
        problem
    )
    assert calls == []
    assert branch_options[0] == (0, (0, 1))
    assert (
        disabled.complete_solutions_evaluated
        == 2 * enabled.complete_solutions_evaluated
    )
    assert disabled.nodes_visited > enabled.nodes_visited
    assert enabled.score == disabled.score == 50
    assert SolutionSignature.from_teams(enabled.teams) == SolutionSignature.from_teams(
        disabled.teams
    )


def test_capacity_lookahead_switch_gates_counter_without_disabling_physical_capacity():
    # With exact total capacity, valid states cannot naturally fail this lookahead.
    # Inject its decision at a physically valid root to test wiring/counters.
    class CapacityImpossibleState(GlobalSearchState):
        def validate_capacity_feasibility(self, total_player_count, team_size):
            return False

    problem = make_problem(root=CapacityImpossibleState.empty(2))
    enabled = solver().optimize(problem, incumbent(problem))
    disabled = solver(use_capacity_pruning=False).optimize(problem, incumbent(problem))
    assert enabled.capacity_prunes == 1
    assert disabled.capacity_prunes == 0
    assert disabled.complete_solutions_evaluated > 0
    assert all(len(team.players) == 2 for team in disabled.teams)
    state = problem.root_state.assign_next_player(0, problem.players[0], 2)
    state = state.assign_next_player(0, problem.players[1], 2)
    with pytest.raises(ValueError):
        state.assign_next_player(0, problem.players[2], 2)


def test_seed_lookahead_switch_gates_counter_while_hard_assignment_stays_enabled():
    # Non-protected players first: filling one team leaves too few seed slots.
    problem = make_problem(seeds=(2, 3))
    teams = incumbent(problem, groups=((0, 2), (1, 3)))
    enabled = solver(use_symmetry_breaking=False).optimize(problem, teams)
    disabled = solver(use_symmetry_breaking=False, use_seed_pruning=False).optimize(
        problem, teams
    )
    assert enabled.seed_prunes > 0
    assert disabled.seed_prunes == 0
    assert disabled.complete_solutions_evaluated > 0
    assert all(
        sum(player.seed == 1 for player in team.players) <= 1 for team in disabled.teams
    )
    state = problem.root_state.assign_next_player(0, problem.players[2], 2, 1, 1)
    with pytest.raises(ValueError, match="protected seeds"):
        state.assign_next_player(0, problem.players[3], 2, 1, 1)


def test_power_switch_prevents_interval_work_and_its_score_prune(monkeypatch):
    problem = make_problem()
    state = problem.root_state
    for index in range(4):
        state = state.assign_next_player(index // 2, problem.players[index], 2)
    weights = dict(
        power_weight=1,
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )
    enabled = GlobalBoundCalculator(**weights)
    decision = enabled.evaluate(problem, state, 90)
    assert decision.prune and decision.reason == "upper_bound"
    assert decision.power_upper_bound < 90
    disabled = GlobalBoundCalculator(
        **weights, pruning_policy=GlobalPruningPolicy(use_power_bound=False)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("disabled Power calculations ran")

    monkeypatch.setattr(disabled, "power_intervals", forbidden)
    monkeypatch.setattr(disabled, "_power_upper_bound", forbidden)
    decision = disabled.evaluate(problem, state, 90)
    assert not decision.prune
    assert decision.power_upper_bound == decision.upper_bound == 100
    assert decision.power_intervals == ()


def test_no_incumbent_bound_only_runs_feasibility_and_serializes_none(monkeypatch):
    problem = make_problem()
    calculator = GlobalBoundCalculator()

    def forbidden(*args, **kwargs):
        raise AssertionError("Power bound ran before first solution")

    monkeypatch.setattr(calculator, "power_intervals", forbidden)
    monkeypatch.setattr(calculator, "_power_upper_bound", forbidden)
    decision = calculator.evaluate(problem, problem.root_state, None)
    assert not decision.prune
    assert decision.incumbent_score is None
    assert decision.as_dict()["incumbent_score"] is None
    assert decision.upper_bound == 100


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
def test_present_bound_incumbent_scores_remain_finite(value):
    problem = make_problem()
    with pytest.raises((TypeError, ValueError)):
        GlobalBoundCalculator().evaluate(problem, problem.root_state, value)


@pytest.mark.parametrize("use_incumbent", [True, False])
@pytest.mark.parametrize("seed_pruning", [True, False])
def test_deterministic_replay_covers_all_structural_counters(
    use_incumbent, seed_pruning
):
    def execute():
        problem = make_problem(seeds=(2, 3))
        optimizer = solver(
            use_incumbent=use_incumbent,
            use_seed_pruning=seed_pruning,
            use_symmetry_breaking=False,
        )
        return optimizer.optimize(
            problem,
            incumbent(problem, groups=((0, 2), (1, 3))) if use_incumbent else None,
        )

    first, second = execute(), execute()
    assert SolutionSignature.from_teams(first.teams) == SolutionSignature.from_teams(
        second.teams
    )
    assert finite_real(first.score, "score") == second.score
    left, right = first.as_dict(), second.as_dict()
    left.pop("elapsed_seconds")
    right.pop("elapsed_seconds")
    assert left == right


@pytest.mark.parametrize("violation", ["capacity", "protected_seeds"])
def test_problem_root_enforces_hard_constraints_independently_of_pruning(violation):
    problem = make_problem(seeds=(0, 1))
    if violation == "capacity":
        state = GlobalSearchState(
            (
                GlobalTeamState(player_indices=(0, 1, 2), player_count=3),
                GlobalTeamState(),
            ),
            next_player_index=3,
            assigned_count=3,
        )
    else:
        state = GlobalSearchState(
            (GlobalTeamState(player_indices=(0, 1), player_count=2), GlobalTeamState()),
            next_player_index=2,
            assigned_count=2,
        )
    with pytest.raises(ValueError, match="hard"):
        replace(problem, root_state=state)


def test_root_builder_seed_validation_is_not_a_pruning_option():
    problem = make_problem(seeds=(0, 1, 2))
    with pytest.raises(ValueError, match="protected seed"):
        GlobalRootBuilder(2, 2).build(problem.players)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("field", ["score", "initial_incumbent_score"])
def test_global_result_validates_every_present_score(field, value):
    result = solver().optimize(make_problem(), incumbent(make_problem()))
    with pytest.raises((TypeError, ValueError)):
        replace(result, **{field: value})


def test_problem_duplicate_logical_identity_is_rejected():
    problem = make_problem()
    duplicate = replace(problem.players[1], player=Player("a"))
    with pytest.raises(ValueError, match="logical identities"):
        replace(problem, players=(problem.players[0], duplicate, *problem.players[2:]))


@pytest.mark.parametrize("stored_count", [0, 2])
def test_root_protected_seed_count_cannot_bypass_assignment_constraint(stored_count):
    problem = make_problem(seeds=(0, 1))
    state = GlobalSearchState(
        (
            GlobalTeamState(
                player_indices=(0,), player_count=1, protected_seed_count=stored_count
            ),
            GlobalTeamState(),
        ),
        next_player_index=1,
        assigned_count=1,
    )
    with pytest.raises(ValueError, match="does not match"):
        replace(problem, root_state=state)
