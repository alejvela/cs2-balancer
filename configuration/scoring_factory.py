"""Explicit construction from typed configuration; no application globals."""

from __future__ import annotations

from configuration.application_config import ScoringConfig
from optimizer.activity.activity_factor_model import (
    ActivityFactorModel,
)
from optimizer.normalization.factory import (
    NormalizerFactory,
)
from scoring.attribute_score_component import (
    AttributeScoreComponent,
)
from scoring.scoring_model import (
    ScoringModel,
)


def create_scoring_model(config: ScoringConfig) -> ScoringModel:
    """Build components and fresh activity model from the validated scoring policy."""

    components = [
        AttributeScoreComponent(
            name=c.name,
            attribute=c.attribute,
            normalizer=NormalizerFactory.logistic(
                midpoint=c.midpoint,
                steepness=c.steepness,
            ),
            default_score=c.default_score,
        )
        for c in config.components
    ]
    weights = {c.name: c.weight for c in config.components}

    return ScoringModel(
        components=components,
        weights=weights,
        minimum_available_weight=config.minimum_available_weight,
        default_power=config.default_power,
        # ScoringConfig validates the sole supported policy: engine_defaults.
        activity_factor_model=ActivityFactorModel(),
    )
