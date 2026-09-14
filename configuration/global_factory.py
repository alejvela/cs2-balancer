"""Explicit construction from typed configuration; no application globals."""

from __future__ import annotations

from collections.abc import Iterable

from configuration.application_config import ApplicationConfig
from objective.objective_engine import (
    ObjectiveEngine,
)
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
)
from optimizer.global_search.global_optimizer import (
    GlobalOptimizer,
)
from optimizer.global_search.global_player_ordering import (
    GlobalPlayerOrdering,
)
from optimizer.global_search.global_root_builder import (
    GlobalRootBuilder,
)
from optimizer.global_search.global_search_problem import (
    GlobalSearchProblem,
)
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
)


def create_global_problem(
    config: ApplicationConfig,
    metrics: Iterable[GlobalPlayerMetrics],
) -> GlobalSearchProblem:
    ordering = GlobalPlayerOrdering(
        protected_seed_level=config.objective.seed_level,
    )

    builder = GlobalRootBuilder(
        number_of_teams=config.event.number_of_teams,
        team_size=config.event.team_size,
        protected_seed_level=config.objective.seed_level,
        maximum_protected_seeds_per_team=config.objective.maximum_per_team,
    )

    return builder.build(
        players=metrics,
        ordering=ordering,
    )


def create_global_optimizer(
    config: ApplicationConfig,
    objective_engine: ObjectiveEngine,
) -> GlobalOptimizer:
    """
    Construye el Branch & Bound GLOBAL.

    Los pesos deben coincidir exactamente con create_objective_engine().
    Solo Power aporta actualmente una cota blanda real; ELO/KD se
    mantienen optimistas a 100 durante la poda.
    """

    bound_calculator = GlobalBoundCalculator(
        power_weight=config.objective.power_weight,
        elo_balance_weight=config.objective.elo_balance_weight,
        elo_spread_weight=config.objective.elo_spread_weight,
        kd_weight=config.objective.kd_weight,
        team_size_weight=config.objective.team_size_weight,
        seed_weight=config.objective.seed_weight,
        score_tolerance=config.global_search.score_tolerance,
    )

    return GlobalOptimizer(
        objective_engine=objective_engine,
        config=config.global_search,
        bound_calculator=bound_calculator,
    )
