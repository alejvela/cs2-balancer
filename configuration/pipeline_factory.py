"""Explicit construction from typed configuration; no application globals."""

from __future__ import annotations

from configuration.application_config import PipelineConfig
from optimizer.neighborhoods.swap_neighborhood import (
    SwapNeighborhood,
)
from optimizer.optimization_phase import (
    OptimizationPhase,
)
from optimizer.optimization_pipeline import (
    OptimizationPipeline,
)
from optimizer.strategies.exhaustive_strategy import (
    ExhaustiveStrategy,
)
from optimizer.strategies.first_improvement_strategy import (
    FirstImprovementStrategy,
)


def create_pipeline(config: PipelineConfig) -> OptimizationPipeline:
    """Translate declared phases into independent mutable engine collaborators."""

    pipeline = OptimizationPipeline()
    strategies = {
        "first_improvement": FirstImprovementStrategy,
        "exhaustive": ExhaustiveStrategy,
    }
    neighborhoods = {"swap": SwapNeighborhood}
    for phase in config.phases:
        pipeline.add(
            OptimizationPhase(
                name=phase.name,
                neighborhood=neighborhoods[phase.neighborhood](),
                strategy=strategies[phase.strategy](
                    minimum_improvement=phase.minimum_improvement,
                ),
                max_iterations=phase.max_iterations,
                enabled=phase.enabled,
                stop_when_no_move=phase.stop_when_no_move,
            )
        )
    return pipeline
