"""Independent labeled-assignment oracle for SCRUM-50 (never calls a bound)."""

from dataclasses import replace
from itertools import product
from math import inf, nextafter

import pytest

from application.results.global_report_result import GlobalReportResult
from models.numeric import finite_real
from models.player import Player
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from objective.restriction import Restriction
from objective.restriction_result import RestrictionResult
from objective.restrictions.elo_balance_restriction import EloBalanceRestriction
from objective.restrictions.elo_spread_restriction import EloSpreadRestriction
from objective.restrictions.kd_balance_restriction import KdBalanceRestriction
from objective.restrictions.power_balance_restriction import PowerBalanceRestriction
from objective.restrictions.seed_separation_restriction import SeedSeparationRestriction
from objective.restrictions.team_size_restriction import TeamSizeRestriction
from optimizer.global_search.global_bound_calculator import GlobalBoundCalculator
from optimizer.global_search.global_bound_safety import (
    assess_compatibility,
    certified_decision,
)
from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.global_search.global_optimizer import GlobalOptimizer
from optimizer.global_search.global_root_builder import GlobalRootBuilder
from optimizer.global_search.global_search_problem import GlobalSearchProblem
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
    GlobalTeamState,
)
from optimizer.normalization.linear_normalizer import LinearNormalizer
from scoring.attribute_score_component import AttributeScoreComponent
from scoring.scoring_model import ScoringModel


# These two functions are the reference, independently constructing and filtering
# all labeled distributions from players/hard constraints, ignoring prepared root.
def valid_distributions(problem):
    for destinations in product(
        range(problem.number_of_teams), repeat=len(problem.players)
    ):
        indices = [
            [index for index, team in enumerate(destinations) if team == number]
            for number in range(problem.number_of_teams)
        ]
        if any(len(group) != problem.team_size for group in indices):
            continue
        if any(
            sum(
                problem.protected_seed_level is not None
                and problem.players[index].seed == problem.protected_seed_level
                for index in group
            )
            > problem.maximum_protected_seeds_per_team
            for group in indices
        ):
            continue
        teams = [
            Team(number + 1, [problem.players[index].player for index in group])
            for number, group in enumerate(indices)
        ]
        yield destinations, teams


def reference_score(objective, teams):
    result = objective.evaluate(teams)
    return finite_real(
        result if isinstance(result, (int, float)) else result.score, "oracle score"
    )


def oracle(problem, objective):
    candidates = [
        (destinations, teams, reference_score(objective, teams))
        for destinations, teams in valid_distributions(problem)
    ]
    assert candidates
    return candidates, max(score for _, _, score in candidates)


class ExtraRestriction(Restriction):
    @property
    def name(self):
        return "Unmodeled grouping"

    def evaluate(self, teams):
        paired = any({"A", "D"} <= {p.nick for p in team.players} for team in teams)
        return RestrictionResult(self.name, 100 if paired else 0, weight=self.weight)


class LabeledObjective:
    def evaluate(self, teams):
        return 150.0 if any(p.nick == "A" for p in teams[0].players) else 23.0


def fixture(kind="power", *, teams=2, size=2, seeded=False, maximum=1, kd_values=None):
    kd_values = kd_values or (80.7, 5.1, 47.3, 20.9, 11.1, 68.8)[: teams * size]
    players = [
        Player(
            chr(65 + i),
            elo=1200 + i * 173,
            kd=kd,
            seed=1 if seeded and (i < 2 or maximum == 2) else None,
        )
        for i, kd in enumerate(kd_values)
    ]
    component = AttributeScoreComponent("signal", "kd", LinearNormalizer(0, 100))
    model = ScoringModel([component], {"signal": 1})
    power = PowerBalanceRestriction(model, weight=3)
    restrictions = [power]
    weights = (3, 0, 0, 0, 0, 0)
    if kind in ("mixed", "misweighted", "reordered"):
        restrictions += [
            EloBalanceRestriction(weight=2),
            EloSpreadRestriction(weight=5),
            KdBalanceRestriction(weight=4),
            TeamSizeRestriction(2, weight=1),
            SeedSeparationRestriction(seed_level=1, maximum_per_team=maximum, weight=2),
        ]
        weights = (3, 2, 5, 4, 1, 2)
        if kind == "misweighted":
            weights = (90, 1, 1, 1, 1, 1)
        if kind == "reordered":
            restrictions.reverse()
    elif kind == "extra":
        restrictions += [ExtraRestriction(weight=2)]
    elif kind == "seed-soft-mismatch":
        players[2].seed = 2
        restrictions += [
            SeedSeparationRestriction(seed_level=2, maximum_per_team=0, weight=2)
        ]
        weights = (3, 0, 0, 0, 0, 2)
    objective = LabeledObjective() if kind == "order" else ObjectiveEngine(restrictions)
    metrics = [
        GlobalPlayerMetrics(p, model.power(p), p.elo, p.kd, p.seed) for p in players
    ]
    if kind == "wrong-metrics":
        metrics = [
            replace(m, power=100 if index < 2 else 0) for index, m in enumerate(metrics)
        ]
    problem = GlobalRootBuilder(
        teams,
        size,
        protected_seed_level=1 if seeded else None,
        maximum_protected_seeds_per_team=maximum,
    ).build(metrics)
    return problem, objective, weights


def run_solver(
    problem,
    objective,
    weights,
    *,
    incumbent=True,
    power=True,
    symmetry=True,
    proof=True,
    **options,
):
    config = GlobalOptimizationConfig(
        maximum_nodes=None,
        maximum_evaluations=None,
        maximum_elapsed_seconds=None,
        use_incumbent=incumbent,
        use_power_bound=power,
        use_symmetry_breaking=symmetry,
        require_proof=proof,
        **options,
    )
    names = (
        "power_weight",
        "elo_balance_weight",
        "elo_spread_weight",
        "kd_weight",
        "team_size_weight",
        "seed_weight",
    )
    calculator = GlobalBoundCalculator(
        **dict(zip(names, weights, strict=True)), pruning_policy=config.pruning_policy
    )
    initial = next(valid_distributions(problem))[1] if incumbent else None
    return GlobalOptimizer(objective, config, calculator).optimize(problem, initial)


@pytest.mark.parametrize(
    "kind",
    [
        "power",
        "mixed",
        "misweighted",
        "reordered",
        "extra",
        "order",
        "wrong-metrics",
        "seed-soft-mismatch",
    ],
)
@pytest.mark.parametrize(
    "incumbent,power,symmetry", list(product((False, True), repeat=3))
)
def test_reference_optimum_and_proof_for_every_switch_combination(
    kind, incumbent, power, symmetry
):
    problem, objective, weights = fixture(kind, seeded=True)
    candidates, best = oracle(problem, objective)
    result = run_solver(
        problem, objective, weights, incumbent=incumbent, power=power, symmetry=symmetry
    )
    assert result.score == best
    assert reference_score(objective, result.teams) == best
    assert result.optimality_proven and result.search_exhausted
    assert result.proof_certificate.optimality_proven
    serialized = result.as_dict()
    assert serialized["search_exhausted"] is True
    assert serialized["proof_certificate"]["search_exhausted"] is True
    assert len(candidates) == 4
    if kind in ("order", "extra"):
        assert result.proof_certificate.root_expanded
    if kind == "order":
        assert result.bound_prunes == 0
        assert result.proof_certificate.bound_strategy == "exhaustive-no-score-bound"
    if kind in ("extra", "misweighted", "wrong-metrics"):
        assert result.proof_certificate.bound_strategy == "objective-ceiling"
    assert (
        result.initial_incumbent_score is not None
        if incumbent
        else result.initial_incumbent_score is None
    )


@pytest.mark.parametrize("kind", ["power", "mixed", "reordered", "extra", "order"])
def test_ordinary_exhaustive_runs_are_certified_only_with_complete_exact_evidence(kind):
    problem, objective, weights = fixture(kind)
    _, best = oracle(problem, objective)
    result = run_solver(problem, objective, weights, proof=False)
    assert result.score == best
    if result.optimality_proven:
        assert result.proof_certificate.optimality_proven
    assert result.search_exhausted


@pytest.mark.parametrize("kind", ["power", "mixed", "reordered"])
@pytest.mark.parametrize(
    "values",
    [
        (0.0, nextafter(0.0, inf), 99.99999999999999, 100.0),
        (80.7, 5.1, 47.3, 20.9),
        (1e-10, 1e-8, 0.3333333333333333, 99.9999999999),
    ],
)
def test_outward_bound_dominates_every_reference_descendant_exactly(kind, values):
    problem, objective, weights = fixture(kind, kd_values=values)
    config = GlobalOptimizationConfig(
        require_proof=True,
        maximum_nodes=None,
        maximum_evaluations=None,
        maximum_elapsed_seconds=None,
    )
    calculator = GlobalBoundCalculator(
        **dict(
            zip(
                (
                    "power_weight",
                    "elo_balance_weight",
                    "elo_spread_weight",
                    "kd_weight",
                    "team_size_weight",
                    "seed_weight",
                ),
                weights,
                strict=True,
            )
        ),
        pruning_policy=config.pruning_policy,
    )
    binding = assess_compatibility(objective, problem, calculator)
    assert binding.power_compatible
    candidates, _ = oracle(problem, objective)
    prefixes = {
        destinations[:depth] for destinations, _, _ in candidates for depth in range(5)
    }
    for prefix in prefixes:
        state = GlobalSearchState.empty(2)
        for index, team in enumerate(prefix):
            state = state.assign_next_player(
                team, problem.players[index], 2, protected_seed_level=None
            )
        best = max(
            score
            for destinations, _, score in candidates
            if destinations[: len(prefix)] == prefix
        )
        upper = binding.upper_bound(problem, state)
        assert upper >= best  # deliberately no tolerance allowance
        decision, safe = certified_decision(
            calculator, binding, problem, state, nextafter(best, -inf), True
        )
        assert not decision.prune
        assert safe


def test_unproved_metric_values_cannot_use_even_weight_matching_power_bound():
    problem, objective, weights = fixture("wrong-metrics")
    calculator = GlobalBoundCalculator(
        power_weight=3,
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )
    binding = assess_compatibility(objective, problem, calculator)
    assert not binding.power_compatible
    # Find a concrete unsound legacy estimate against the authoritative objective.
    witnessed = False
    for destinations, teams in valid_distributions(problem):
        state = GlobalSearchState.empty(2)
        for index, team in enumerate(destinations):
            state = state.assign_next_player(
                team, problem.players[index], 2, protected_seed_level=None
            )
        score = reference_score(objective, teams)
        raw = calculator.evaluate(problem, state, 0)
        if raw.upper_bound < score:
            decision, safe = certified_decision(
                calculator, binding, problem, state, (raw.upper_bound + score) / 2, True
            )
            assert not decision.prune and safe
            witnessed = True
    assert witnessed


def test_multi_seed_root_is_not_a_permutation_representative():
    problem, objective, weights = fixture(seeded=True, maximum=2)
    _, best = oracle(problem, objective)
    ordinary = run_solver(problem, objective, weights, proof=False)
    assert ordinary.search_exhausted
    assert not ordinary.optimality_proven
    assert not ordinary.proof_certificate.root_complete
    strict = run_solver(problem, objective, weights)
    assert strict.proof_certificate.root_expanded
    assert strict.score == best and strict.optimality_proven


def test_unknown_team_label_objective_expands_seed_root_even_outside_proof_mode():
    problem, objective, weights = fixture("order", seeded=True)
    _, best = oracle(problem, objective)
    result = run_solver(problem, objective, weights, proof=False)
    assert result.score == best == 150
    assert result.proof_certificate.root_expanded
    assert result.optimality_proven


def test_three_team_metric_floating_symmetry_is_not_assumed_in_proof_mode(monkeypatch):
    problem, objective, weights = fixture("mixed", teams=3)
    _, best = oracle(problem, objective)

    def forbidden(*args, **kwargs):
        raise AssertionError("unverified floating symmetry used")

    monkeypatch.setattr(
        GlobalSearchState, "canonical_available_team_indices", forbidden
    )
    result = run_solver(problem, objective, weights)
    assert result.score == best and result.optimality_proven
    assert result.complete_solutions_evaluated <= 90
    assert result.proof_certificate.symmetry_safe


@pytest.mark.parametrize("incumbent", [False, True])
def test_near_tolerance_improvement_is_never_lost_in_proof_mode(incumbent):
    problem, _, weights = fixture()
    first = next(valid_distributions(problem))[1]
    initial_group = frozenset(p.nick for p in first[0].players)

    class TinyImprovement:
        def evaluate(self, teams):
            return (
                50.0
                if frozenset(p.nick for p in teams[0].players) == initial_group
                else 50.0000001
            )

    objective = TinyImprovement()
    _, best = oracle(problem, objective)
    approximate = run_solver(
        problem,
        objective,
        weights,
        proof=False,
        incumbent=incumbent,
        minimum_improvement=1,
        score_tolerance=0.01,
    )
    assert approximate.search_exhausted and not approximate.optimality_proven
    assert not approximate.proof_certificate.ranking_exact
    strict = run_solver(
        problem,
        objective,
        weights,
        incumbent=incumbent,
        minimum_improvement=1,
        score_tolerance=0.01,
    )
    assert strict.score == best and strict.optimality_proven


@pytest.mark.parametrize(
    "limit,value,reason",
    [
        ("maximum_nodes", 1, "NODE_LIMIT"),
        ("maximum_evaluations", 1, "EVALUATION_LIMIT"),
        ("maximum_elapsed_seconds", 1e-9, "TIME_LIMIT"),
    ],
)
def test_budget_termination_cannot_certify_even_when_result_happens_to_be_best(
    limit, value, reason
):
    problem, objective, weights = fixture("order", seeded=True)
    config = GlobalOptimizationConfig(
        maximum_nodes=None, maximum_evaluations=None, maximum_elapsed_seconds=None, **{}
    )
    config = replace(config, **{limit: value})
    calculator = GlobalBoundCalculator(pruning_policy=config.pruning_policy)
    result = GlobalOptimizer(objective, config, calculator).optimize(
        problem, next(valid_distributions(problem))[1]
    )
    assert result.stopped_by_limit and result.stop_reason == reason
    assert not result.search_exhausted and not result.optimality_proven
    assert not result.proof_certificate.search_exhausted


@pytest.mark.parametrize(
    "limit", ["maximum_nodes", "maximum_evaluations", "maximum_elapsed_seconds"]
)
def test_require_proof_keeps_explicit_rejection_of_configured_budgets(limit):
    with pytest.raises(ValueError, match="require_proof=True requires"):
        replace(GlobalOptimizationConfig.proof(), **{limit: 1})


def test_exhaustion_and_proof_not_completed_are_separate_result_facts():
    problem, _, _ = fixture()
    holder = []

    class UnableToCertify:
        def evaluate(self, teams):
            # Simulate an external audit veto without replacing the DFS.
            holder[0]._ranking_exact = False
            return 50.0

    config = GlobalOptimizationConfig.proof()
    calculator = GlobalBoundCalculator(pruning_policy=config.pruning_policy)
    optimizer = GlobalOptimizer(UnableToCertify(), config, calculator)
    holder.append(optimizer)
    result = optimizer.optimize(problem, next(valid_distributions(problem))[1])
    assert result.search_exhausted and not result.optimality_proven
    assert result.stop_reason == "PROOF_NOT_COMPLETED"
    from objective.objective_result import ObjectiveResult

    report = GlobalReportResult(
        result.teams,
        ObjectiveResult(score=result.score),
        result.initial_incumbent_score,
        result,
    )
    assert report.search_exhausted and not report.optimality_proven
    assert report.proof_certificate is result.proof_certificate


@pytest.mark.parametrize("proof", [False, True])
def test_final_score_drift_inside_tolerance_cannot_contribute_to_proof(proof):
    problem, _, weights = fixture()

    class DriftingObjective:
        calls = 0

        def evaluate(self, teams):
            self.calls += 1
            return 50.0 if self.calls <= 6 else 50.0 - 1e-7

    if proof:
        with pytest.raises(RuntimeError, match="exact independent final score"):
            run_solver(problem, DriftingObjective(), weights, incumbent=False)
    else:
        result = run_solver(
            problem, DriftingObjective(), weights, incumbent=False, proof=False
        )
        assert result.search_exhausted and not result.optimality_proven
        assert not result.proof_certificate.final_score_exact


def test_result_cannot_claim_proof_without_evidence_or_after_budget_termination():
    problem, objective, weights = fixture()
    result = run_solver(problem, objective, weights)
    with pytest.raises(ValueError, match="certificate"):
        replace(result, proof_certificate=None)
    with pytest.raises(ValueError, match="Budget termination"):
        replace(result, stopped_by_limit=True)
    with pytest.raises(ValueError, match="agree"):
        replace(
            result,
            proof_certificate=replace(result.proof_certificate, root_complete=False),
        )


def test_root_must_cover_its_actual_prefix_before_any_proof():
    problem, _, _ = fixture()
    root = GlobalSearchState(
        (GlobalTeamState(player_indices=(2,), player_count=1), GlobalTeamState()),
        next_player_index=1,
        assigned_count=1,
    )
    with pytest.raises(ValueError, match="sequential player prefix"):
        replace(problem, root_state=root)


def test_unknown_calculator_cannot_force_score_prunes_with_matching_weights():
    from dataclasses import replace

    problem, objective, _ = fixture("order", seeded=True)
    _, best = oracle(problem, objective)

    class UnsafeCalculator(GlobalBoundCalculator):
        def evaluate(self, problem, state, incumbent_score):
            return replace(
                super().evaluate(problem, state, None),
                upper_bound=0,
                prune=True,
                reason="upper_bound",
            )

    config = GlobalOptimizationConfig.proof()
    calculator = UnsafeCalculator(pruning_policy=config.pruning_policy)
    result = GlobalOptimizer(objective, config, calculator).optimize(
        problem, next(valid_distributions(problem))[1]
    )
    assert result.score == best and result.optimality_proven
    assert result.bound_prunes == 0
    binding = assess_compatibility(objective, problem, calculator)
    decision, safe = certified_decision(
        calculator, binding, problem, GlobalSearchState.empty(2), 23, True
    )
    assert decision.upper_bound is None and not decision.prune and safe


def test_unknown_feasibility_callback_is_independently_checked_in_proof_mode():
    problem, objective, _ = fixture("order", seeded=True)
    _, best = oracle(problem, objective)

    class UnsafeCalculator(GlobalBoundCalculator):
        def evaluate(self, problem, state, incumbent_score):
            return replace(
                super().evaluate(problem, state, None),
                prune=True,
                reason="seed_impossible",
                feasible=False,
            )

    config = GlobalOptimizationConfig.proof()
    result = GlobalOptimizer(
        objective, config, UnsafeCalculator(pruning_policy=config.pruning_policy)
    ).optimize(problem, next(valid_distributions(problem))[1])
    assert result.score == best and result.optimality_proven


def test_replaced_builtin_evaluator_is_not_certified_by_its_class_name(monkeypatch):
    problem, objective, weights = fixture(seeded=True)

    def replacement(self, teams):
        score = 99 if any(p.nick == "A" for p in teams[0].players) else 20
        return RestrictionResult(self.name, score, weight=self.weight)

    monkeypatch.setattr(PowerBalanceRestriction, "evaluate", replacement)
    _, best = oracle(problem, objective)
    result = run_solver(problem, objective, weights)
    assert result.score == best and result.optimality_proven
    assert result.proof_certificate.bound_strategy == "objective-ceiling"
    assert result.proof_certificate.root_expanded


@pytest.mark.parametrize("kind", ["symmetry", "ordering"])
def test_unverified_search_reductions_fail_explicitly_when_proof_is_required(
    kind, monkeypatch
):
    problem, objective, weights = fixture()
    if kind == "symmetry":
        monkeypatch.setattr(
            GlobalSearchState, "canonical_available_team_indices", lambda *args: ()
        )
    else:
        monkeypatch.setattr(
            GlobalOptimizer, "_order_candidate_teams", lambda *args, **kwargs: ()
        )
    with pytest.raises(RuntimeError, match="candidate|permutation"):
        run_solver(problem, objective, weights)


def test_non_hard_assignment_failure_cannot_be_mislabeled_as_safe_pruning():
    problem, _, weights = fixture()
    metrics = tuple(replace(item, elo=1e308) for item in problem.players)
    problem = replace(problem, players=metrics)

    class Constant:
        def evaluate(self, teams):
            return 50.0

    ordinary = run_solver(problem, Constant(), weights, proof=False)
    assert not ordinary.optimality_proven
    assert not ordinary.proof_certificate.feasibility_pruning_safe
    with pytest.raises(ValueError, match="finite"):
        run_solver(problem, Constant(), weights)


def test_fresh_incumbent_stays_supported_but_proof_needs_an_objective_witness():
    problem, objective, weights = fixture()
    first = next(valid_distributions(problem))[1]
    fresh = [
        Team(
            i + 1,
            [Player(p.nick, elo=p.elo, kd=p.kd, seed=p.seed) for p in group.players],
        )
        for i, group in enumerate(first)
    ]
    config = GlobalOptimizationConfig.proof()
    calculator = GlobalBoundCalculator(pruning_policy=config.pruning_policy)
    result = GlobalOptimizer(objective, config, calculator).optimize(problem, fresh)
    assert result.optimality_proven
    assert result.proof_certificate.incumbent_in_domain

    class ObjectSensitive:
        def evaluate(self, teams):
            return (
                90.0
                if any(
                    p is fresh[0].players[0] for group in teams for p in group.players
                )
                else 50.0
            )

    with pytest.raises(RuntimeError, match="exact witness"):
        GlobalOptimizer(ObjectSensitive(), config, calculator).optimize(problem, fresh)


def test_replaced_builtin_helper_is_not_certified_by_unchanged_evaluate_method(
    monkeypatch,
):
    problem, objective, weights = fixture(seeded=True)
    original = PowerBalanceRestriction._calculate_team_power

    def helper(self, team):
        result = original(self, team)
        result["average_power"] = (
            90 if any(p.nick == "A" for p in team.players) and team.id == 1 else 20
        )
        return result

    monkeypatch.setattr(PowerBalanceRestriction, "_calculate_team_power", helper)
    _, best = oracle(problem, objective)
    result = run_solver(problem, objective, weights)
    assert result.score == best and result.optimality_proven
    assert result.proof_certificate.bound_strategy == "objective-ceiling"
    assert result.proof_certificate.root_expanded


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -float("inf")])
def test_mutated_nonfinite_bound_is_rejected_before_safe_fallback(value):
    problem, objective, _ = fixture("order")

    class Malformed(GlobalBoundCalculator):
        def evaluate(self, problem, state, incumbent_score):
            result = super().evaluate(problem, state, None)
            object.__setattr__(result, "upper_bound", value)
            return result

    config = GlobalOptimizationConfig.proof()
    with pytest.raises((TypeError, ValueError)):
        GlobalOptimizer(
            objective, config, Malformed(pruning_policy=config.pruning_policy)
        ).optimize(problem, next(valid_distributions(problem))[1])


@pytest.mark.parametrize("kind", ["power", "mixed", "reordered"])
def test_non_dyadic_team_means_are_enclosed_for_every_three_player_completion(kind):
    problem, objective, weights = fixture(
        kind, size=3, kd_values=(0.1, 0.2, 2e-10, 98.1, 99.3, 99.7)
    )
    calculator = GlobalBoundCalculator(
        **dict(
            zip(
                (
                    "power_weight",
                    "elo_balance_weight",
                    "elo_spread_weight",
                    "kd_weight",
                    "team_size_weight",
                    "seed_weight",
                ),
                weights,
                strict=True,
            )
        )
    )
    binding = assess_compatibility(objective, problem, calculator)
    assert binding.power_compatible
    candidates, best = oracle(problem, objective)
    prefixes = {
        destinations[:depth] for destinations, _, _ in candidates for depth in range(7)
    }
    for prefix in prefixes:
        state = GlobalSearchState.empty(2)
        for index, team in enumerate(prefix):
            state = state.assign_next_player(
                team, problem.players[index], 3, protected_seed_level=None
            )
        descendant = max(
            score for dest, _, score in candidates if dest[: len(prefix)] == prefix
        )
        assert binding.upper_bound(problem, state) >= descendant
    result = run_solver(problem, objective, weights)
    assert result.score == best and result.optimality_proven


def test_mutated_logical_pool_is_revalidated_even_without_incumbent():
    problem, objective, weights = fixture()
    problem.players[1].player.nick = problem.players[0].player.nick
    with pytest.raises(ValueError, match="duplicated logical identities"):
        run_solver(problem, objective, weights, incumbent=False)


def test_team_object_identity_cannot_certify_an_incumbent_from_metadata_alone():
    problem, _, _ = fixture()
    initial = next(valid_distributions(problem))[1]

    class IdentitySensitive:
        def evaluate(self, teams):
            return (
                90.0
                if all(a is b for a, b in zip(teams, initial, strict=True))
                else 50.0
            )

    config = GlobalOptimizationConfig.proof()
    with pytest.raises(RuntimeError, match="exact witness"):
        GlobalOptimizer(
            IdentitySensitive(),
            config,
            GlobalBoundCalculator(pruning_policy=config.pruning_policy),
        ).optimize(problem, initial)


def test_stale_statistics_cache_cannot_certify_a_canonical_incumbent():
    problem, objective, _ = fixture("mixed")
    initial = next(valid_distributions(problem))[1]
    objective.evaluate(initial)
    for team in initial:
        team.statistics._cache[("avg", "elo")] = 1000.0
    config = GlobalOptimizationConfig.proof()
    with pytest.raises(RuntimeError, match="exact witness"):
        GlobalOptimizer(
            objective,
            config,
            GlobalBoundCalculator(pruning_policy=config.pruning_policy),
        ).optimize(problem, initial)


def test_unknown_traversal_cannot_return_proof_from_an_exhaustion_label():
    problem, objective, _ = fixture()

    class SkipsSearch(GlobalOptimizer):
        def _search(self, state):
            return None

    config = GlobalOptimizationConfig.proof()
    calculator = GlobalBoundCalculator(pruning_policy=config.pruning_policy)
    with pytest.raises(RuntimeError, match="verified traversal"):
        SkipsSearch(objective, config, calculator).optimize(
            problem, next(valid_distributions(problem))[1]
        )
    ordinary = replace(config, require_proof=False)
    result = SkipsSearch(objective, ordinary, calculator).optimize(
        problem, next(valid_distributions(problem))[1]
    )
    assert not result.optimality_proven
    assert not result.proof_certificate.traversal_verified


def test_unverified_next_player_cannot_omit_valid_assignments():
    problem, objective, _ = fixture()

    class WrongNextPlayer(GlobalSearchProblem):
        def next_player(self, state):
            return self.players[0]

    problem = WrongNextPlayer(
        problem.players,
        problem.root_state,
        problem.number_of_teams,
        problem.team_size,
        problem.protected_seed_level,
        problem.maximum_protected_seeds_per_team,
    )
    config = GlobalOptimizationConfig.proof()
    with pytest.raises(RuntimeError, match="canonical problem prefix"):
        GlobalOptimizer(
            objective,
            config,
            GlobalBoundCalculator(pruning_policy=config.pruning_policy),
        ).optimize(problem, next(valid_distributions(problem))[1])

@pytest.mark.parametrize("attribute", ["weighted_score", "_validate_score"])
def test_modified_restriction_result_implementation_disables_power_tightening(
    monkeypatch, attribute
):
    problem, objective, weights = fixture("power")
    calculator = GlobalBoundCalculator(
        power_weight=weights[0],
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )
    assert assess_compatibility(objective, problem, calculator).power_compatible

    original = getattr(RestrictionResult, attribute)
    if isinstance(original, property):
        monkeypatch.setattr(
            RestrictionResult, attribute,
            property(lambda self: 0.0),
        )
    else:
        monkeypatch.setattr(
            RestrictionResult, attribute,
            classmethod(lambda cls, value: 0.0),
        )

    binding = assess_compatibility(objective, problem, calculator)
    assert not binding.power_compatible
    assert binding.strategy == "objective-ceiling"


@pytest.mark.parametrize("constant", ["SCORE_MINIMUM", "SCORE_MAXIMUM"])
def test_modified_restriction_result_score_limits_disable_power_tightening(
    monkeypatch, constant
):
    problem, objective, weights = fixture("power")
    calculator = GlobalBoundCalculator(
        power_weight=weights[0],
        elo_balance_weight=0,
        elo_spread_weight=0,
        kd_weight=0,
        team_size_weight=0,
        seed_weight=0,
    )
    assert assess_compatibility(objective, problem, calculator).power_compatible
    monkeypatch.setattr(RestrictionResult, constant, 1.0 if constant == "SCORE_MINIMUM" else 99.0)
    binding = assess_compatibility(objective, problem, calculator)
    assert not binding.power_compatible
    assert binding.strategy == "objective-ceiling"
