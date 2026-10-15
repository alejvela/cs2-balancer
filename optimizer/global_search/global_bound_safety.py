"""Checked objective bindings and outward-rounded bounds. See the audit in docs."""

import sys
from dataclasses import dataclass, replace
from fractions import Fraction
from math import inf, isfinite, nextafter, ulp

from models.numeric import finite_real
from models.player import Player
from models.player_identity import logical_player_identity
from models.team_statistics import TeamStatistics
from objective.objective_engine import ObjectiveEngine
from objective.objective_result import ObjectiveResult
from objective.restriction_result import RestrictionResult
from objective.restrictions.elo_balance_restriction import EloBalanceRestriction
from objective.restrictions.elo_spread_restriction import EloSpreadRestriction
from objective.restrictions.kd_balance_restriction import KdBalanceRestriction
from objective.restrictions.power_balance_restriction import PowerBalanceRestriction
from objective.restrictions.seed_separation_restriction import SeedSeparationRestriction
from objective.restrictions.team_size_restriction import TeamSizeRestriction
from optimizer.activity.activity_factor_model import ActivityFactorModel
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
    GlobalBoundResult,
)
from optimizer.global_search.global_search_state import GlobalSearchState
from optimizer.normalization.linear_normalizer import LinearNormalizer
from optimizer.normalization.logistic_normalizer import LogisticNormalizer
from optimizer.statistics.statistics_utils import StatisticsUtils
from scoring.attribute_score_component import AttributeScoreComponent
from scoring.scoring_model import ScoringModel

_TYPES = (
    PowerBalanceRestriction,
    EloBalanceRestriction,
    EloSpreadRestriction,
    KdBalanceRestriction,
    TeamSizeRestriction,
    SeedSeparationRestriction,
)
_SCORING_POWER = ScoringModel.power
_BOUND_METHODS = {
    name: getattr(GlobalBoundCalculator, name)
    for name in (
        "evaluate",
        "evaluate_feasibility",
        "_seed_feasible",
        "power_intervals",
        "_power_upper_bound",
        "_elo_upper_bound",
        "_kd_upper_bound",
        "_combine_upper_bounds",
        "minimum_unavoidable_power_spread",
        "minimum_unavoidable_power_stddev",
    )
}
_NORMALIZERS = {
    LogisticNormalizer: LogisticNormalizer.normalize,
    LinearNormalizer: LinearNormalizer.normalize,
}


_IMPLEMENTATIONS = {
    kind: {
        name: (
            getattr(kind, name).__func__
            if hasattr(getattr(kind, name), "__func__")
            else getattr(kind, name)
        )
        for name in dir(kind)
        if not name.startswith("__") and callable(getattr(kind, name))
    }
    for kind in (
        *_TYPES,
        ObjectiveEngine,
        ObjectiveResult,
        RestrictionResult,
        ScoringModel,
        AttributeScoreComponent,
        ActivityFactorModel,
        LogisticNormalizer,
        LinearNormalizer,
        StatisticsUtils,
        TeamStatistics,
        Player,
    )
}

_PROPERTIES = {
    kind: {
        name: getattr(kind, name)
        for name in dir(kind)
        if isinstance(getattr(kind, name), property)
    }
    for kind in _IMPLEMENTATIONS
}


def _class_implementation_unchanged(kind) -> bool:
    return all(
        getattr(kind, name) is item for name, item in _PROPERTIES[kind].items()
    ) and all(
        getattr(getattr(kind, name), "__func__", getattr(kind, name)) is method
        for name, method in _IMPLEMENTATIONS[kind].items()
    )


def _known_implementation(obj, kind) -> bool:
    return (
        type(obj) is kind
        and _class_implementation_unchanged(kind)
        and all(
            getattr(getattr(obj, name), "__func__", getattr(obj, name)) is method
            for name, method in _IMPLEMENTATIONS[kind].items()
        )
        and _no_callable_overrides(obj)
    )


def _known_scoring(model) -> bool:
    if not _known_implementation(model, ScoringModel):
        return False
    activity = model.activity_factor_model
    if activity is not None and not _known_implementation(
        activity, ActivityFactorModel
    ):
        return False
    for component in model.components:
        if not _known_implementation(component, AttributeScoreComponent):
            return False
        normalizer = component.normalizer
        if type(normalizer) not in _NORMALIZERS or not _known_implementation(
            normalizer, type(normalizer)
        ):
            return False
    return True


def _unchanged_method(obj, name, expected) -> bool:
    return getattr(getattr(obj, name, None), "__func__", None) is expected


def _no_callable_overrides(obj) -> bool:
    return not any(callable(value) for value in vars(obj).values())


@dataclass(frozen=True, slots=True)
class BoundCompatibility:
    score_ceiling: float | None
    symmetric: bool
    bitwise_symmetric: bool
    power_compatible: bool
    calculator_trusted: bool
    powers: tuple[float, ...]
    terms: tuple[tuple[bool, float], ...]
    strategy: str

    def upper_bound(self, problem, state) -> float | None:
        if not self.power_compatible:
            return self.score_ceiling
        # Exact rational sums of input binary64 values; include an error envelope
        # for the target's sequential/compensated float sum, not just real arithmetic.
        largest = max(self.powers)
        size = problem.team_size
        if largest == 0:
            power_bound = 100.0
        else:
            magnitude = nextafter(float(Fraction(largest) * (2 * size)), inf)
            error = Fraction(ulp(magnitude)) * (8 * size + 8)
            remaining = sorted(
                Fraction(value) for value in self.powers[state.next_player_index :]
            )
            lows, highs = [], []
            for team in state.teams:
                slots = size - team.player_count
                fixed = sum(
                    (Fraction(self.powers[index]) for index in team.player_indices),
                    Fraction(),
                )
                low = max(
                    Fraction(), fixed + sum(remaining[:slots], Fraction()) - error
                )
                high = (
                    fixed
                    + (sum(remaining[-slots:], Fraction()) if slots else Fraction())
                    + error
                )
                lows.append(max(0.0, nextafter(float(low / size), -inf)))
                highs.append(nextafter(float(high / size), inf))
            spread = max(0.0, nextafter(max(lows) - min(highs), -inf))
            mean_upper = nextafter(
                float(sum(map(Fraction, highs), Fraction()) / len(highs)), inf
            )
            ratio_lower = max(0.0, nextafter(spread / mean_upper, -inf))
            power_bound = min(
                100.0,
                max(0.0, nextafter(100.0 * nextafter(1.0 - ratio_lower, inf), inf)),
            )
        # Actual restriction ordering and actual denominator, not assumed factory
        # order. Nonnegative penalties are optimistically omitted.
        numerator, denominator = 0.0, 0.0
        for is_power, weight in self.terms:
            contribution = (power_bound if is_power else 100.0) * weight
            numerator = nextafter(numerator + nextafter(contribution, inf), inf)
            denominator += weight
        if not isfinite(numerator) or denominator <= 0:
            return 100.0
        return min(
            100.0,
            finite_real(
                nextafter(numerator / denominator, inf), "certified upper bound"
            ),
        )


def assess_compatibility(objective, problem, calculator) -> BoundCompatibility:
    identities = [logical_player_identity(item.player) for item in problem.players]
    if len(set(identities)) != len(identities):
        raise ValueError(
            "Problem contains duplicated logical identities at the search boundary."
        )
    trusted = (
        type(calculator) is GlobalBoundCalculator
        and all(
            getattr(getattr(calculator, name), "__func__", getattr(calculator, name))
            is method
            for name, method in _BOUND_METHODS.items()
        )
        and _no_callable_overrides(calculator)
    )
    engine = (
        _known_implementation(objective, ObjectiveEngine)
        and _class_implementation_unchanged(ObjectiveResult)
        and _class_implementation_unchanged(RestrictionResult)
        and RestrictionResult.SCORE_MAXIMUM == 100.0
        and RestrictionResult.SCORE_MINIMUM == 0.0
        and ObjectiveResult.SCORE_MAXIMUM == 100.0
        and ObjectiveResult.SCORE_MINIMUM == 0.0
    )
    ceiling = 100.0 if engine else None  # ObjectiveResult.compute() explicitly clamps.
    restrictions = objective.restrictions if engine else ()
    known = (
        bool(restrictions)
        and _class_implementation_unchanged(Player)
        and all(type(item.player) is Player for item in problem.players)
        and all(
            type(item) in _TYPES
            and _known_implementation(item, type(item))
            and _class_implementation_unchanged(StatisticsUtils)
            and _class_implementation_unchanged(TeamStatistics)
            for item in restrictions
        )
    )
    if known:
        for item in restrictions:
            if type(item) in (EloBalanceRestriction, KdBalanceRestriction):
                normalizer = item.normalizer
                known = (
                    known
                    and type(normalizer) in _NORMALIZERS
                    and _unchanged_method(
                        normalizer, "normalize", _NORMALIZERS.get(type(normalizer))
                    )
                    and _known_implementation(normalizer, type(normalizer))
                )
            if type(item) is PowerBalanceRestriction:
                model = item.scoring_model
                known = (
                    known
                    and type(model) is ScoringModel
                    and _unchanged_method(model, "power", _SCORING_POWER)
                    and _known_scoring(model)
                )
    # With >2 teams, metric variance's floating reductions are not certified as
    # bitwise permutation invariant. Ordinary ranking keeps its old reduction;
    # proof mode must search labels as well.
    bitwise = known and (
        problem.number_of_teams <= 2
        or not any(
            type(item) in (EloBalanceRestriction, KdBalanceRestriction)
            for item in restrictions
        )
    )
    terms = (
        tuple(
            (
                type(item) is PowerBalanceRestriction,
                finite_real(item.weight, "restriction weight"),
            )
            for item in restrictions
        )
        if known
        else ()
    )
    if any(weight < 0 for _, weight in terms):
        raise ValueError("Restriction weight cannot be negative.")
    actual = (
        tuple(
            sum(
                weight
                for item, (_, weight) in zip(restrictions, terms, strict=True)
                if type(item) is kind
            )
            for kind in _TYPES
        )
        if known
        else ()
    )
    power = next(
        (item for item in restrictions if type(item) is PowerBalanceRestriction), None
    )
    compatible = (
        known
        and trusted
        and power is not None
        and actual == calculator.component_weights
    )
    powers = tuple(finite_real(item.power, "metric Power") for item in problem.players)
    if compatible:
        compatible = all(
            finite_real(power.scoring_model.power(item.player), "objective Power")
            == item.power
            for item in problem.players
        )
        compatible = (
            compatible
            and sys.implementation.name == "cpython"
            and sys.version_info[:2] in ((3, 11), (3, 12), (3, 14))
            and sys.float_info.radix == 2
            and sys.float_info.mant_dig == 53
            and sys.float_info.rounds == 1
        )
        compatible = (
            compatible
            and problem.team_size <= 1_000_000
            and all(0 <= value <= 100 for value in powers)
        )
        largest = max(powers)
        compatible = compatible and (largest == 0 or largest >= 2.0**-500)
    compatible = compatible and all(isfinite(100.0 * weight) for _, weight in terms)
    enabled = compatible and calculator.pruning_policy.use_power_bound
    strategy = (
        "outward-rounded-Power"
        if enabled
        else "objective-ceiling"
        if ceiling is not None
        else "exhaustive-no-score-bound"
    )
    return BoundCompatibility(
        ceiling, known, bitwise, enabled, trusted, powers, terms, strategy
    )


def builder_root(problem) -> bool:
    root = problem.root_state
    count = sum(
        problem.protected_seed_level is not None
        and item.seed == problem.protected_seed_level
        for item in problem.players
    )
    if not count or root.assigned_count != count:
        return False
    if any(
        item.seed != problem.protected_seed_level for item in problem.players[:count]
    ):
        return False
    expected = GlobalSearchState.empty(problem.number_of_teams)
    for item in problem.players[:count]:
        expected = expected.assign_next_player(
            expected.next_player_index % problem.number_of_teams,
            item,
            problem.team_size,
            problem.protected_seed_level,
            problem.maximum_protected_seeds_per_team,
        )
    return root == expected


def select_root(problem, compatibility, require_proof):
    root = problem.root_state
    empty = type(root) is GlobalSearchState and root.assigned_count == 0
    canonical = builder_root(problem)
    complete = empty or (
        canonical
        and compatibility.bitwise_symmetric
        and problem.maximum_protected_seeds_per_team == 1
    )
    # Expand unproved factory reductions for unknown objectives even in ordinary
    # mode; keep arbitrary caller roots in ordinary mode but never certify them.
    if (require_proof and not complete) or (canonical and not compatibility.symmetric):
        return GlobalSearchState.empty(problem.number_of_teams), True
    return root, complete


def certified_decision(
    calculator, compatibility, problem, state, incumbent, require_proof
):
    if compatibility.calculator_trusted and (
        incumbent is None or not compatibility.power_compatible
    ):
        raw = calculator.evaluate_feasibility(problem, state, incumbent)
        if raw is None:
            raw = GlobalBoundResult(
                True,
                compatibility.score_ceiling,
                False,
                None,
                incumbent,
                state.depth,
                True,
                True,
                100.0,
                100.0,
                100.0,
            )
    else:
        raw = calculator.evaluate(
            problem, state, incumbent if compatibility.power_compatible else None
        )
    if not isinstance(raw, GlobalBoundResult):
        raise TypeError("Bound calculator must return GlobalBoundResult.")
    GlobalBoundResult.__post_init__(raw)
    if raw.prune and raw.reason in ("capacity_impossible", "seed_impossible"):
        safe = compatibility.calculator_trusted and type(state) is GlobalSearchState
        if require_proof and not safe:
            if raw.reason == "capacity_impossible":
                justified = (
                    sum(
                        max(0, problem.team_size - team.player_count)
                        for team in state.teams
                    )
                    < problem.player_count - state.assigned_count
                )
            else:
                remaining = (
                    sum(
                        item.seed == problem.protected_seed_level
                        for item in problem.players[state.next_player_index :]
                    )
                    if problem.protected_seed_level is not None
                    else 0
                )
                slots = sum(
                    max(
                        0,
                        min(
                            problem.team_size - team.player_count,
                            problem.maximum_protected_seeds_per_team
                            - team.protected_seed_count,
                        ),
                    )
                    for team in state.teams
                )
                justified = remaining > slots
            return replace(
                raw,
                prune=justified,
                reason=raw.reason if justified else None,
                incumbent_score=incumbent,
            ), True
        return replace(raw, incumbent_score=incumbent), safe
    if raw.prune and raw.reason not in ("upper_bound", None):
        raise RuntimeError("Unknown GLOBAL pruning rule cannot support a proof.")
    upper = compatibility.score_ceiling
    # Legacy bound is only a proposal. No score branch is discarded without the
    # independently enclosed upper bound, including custom calculator overrides.
    if raw.prune and compatibility.power_compatible:
        upper = compatibility.upper_bound(problem, state)
    tolerance = (
        0.0
        if require_proof
        else finite_real(calculator.score_tolerance, "score_tolerance")
    )
    prune = (
        incumbent is not None and upper is not None and upper <= incumbent + tolerance
    )
    safe = not prune or upper <= incumbent
    return replace(
        raw,
        prune=prune,
        reason="upper_bound" if prune else None,
        upper_bound=upper,
        incumbent_score=incumbent,
    ), safe
