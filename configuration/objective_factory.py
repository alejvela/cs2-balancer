"""Explicit construction from typed configuration; no application globals."""

from __future__ import annotations

from configuration.application_config import ObjectiveConfig
from objective.objective_engine import (
    ObjectiveEngine,
)
from objective.restrictions.elo_balance_restriction import (
    EloBalanceRestriction,
)
from objective.restrictions.elo_spread_restriction import (
    EloSpreadRestriction,
)
from objective.restrictions.kd_balance_restriction import (
    KdBalanceRestriction,
)
from objective.restrictions.power_balance_restriction import (
    PowerBalanceRestriction,
)
from objective.restrictions.seed_separation_restriction import (
    SeedSeparationRestriction,
)
from objective.restrictions.team_size_restriction import (
    TeamSizeRestriction,
)
from scoring.scoring_model import (
    ScoringModel,
)


def create_objective_engine(
    config: ObjectiveConfig,
    scoring_model: ScoringModel,
    *,
    team_size: int,
) -> ObjectiveEngine:
    """Build the six ordered restrictions from config and explicit event team size."""

    restrictions = [
        PowerBalanceRestriction(
            scoring_model=scoring_model,
            weight=config.power_weight,
        ),
        EloBalanceRestriction(
            weight=config.elo_balance_weight,
            midpoint=config.elo_midpoint,
            steepness=config.elo_steepness,
        ),
        EloSpreadRestriction(
            weight=config.elo_spread_weight,
            ideal_spread=config.ideal_spread,
            good_spread=config.good_spread,
            acceptable_spread=config.acceptable_spread,
            poor_spread=config.poor_spread,
            maximum_spread=config.maximum_spread,
        ),
        KdBalanceRestriction(
            weight=config.kd_weight,
            max_deviation=config.kd_max_deviation,
        ),
        TeamSizeRestriction(
            expected_size=team_size,
            penalty_per_position=config.penalty_per_position,
            weight=config.team_size_weight,
        ),
        SeedSeparationRestriction(
            seed_level=config.seed_level,
            maximum_per_team=config.maximum_per_team,
            penalty_per_excess_player=config.penalty_per_excess_player,
            maximum_penalty=config.maximum_penalty,
            weight=config.seed_weight,
        ),
    ]

    return ObjectiveEngine(
        restrictions=restrictions,
    )
