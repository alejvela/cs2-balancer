"""Local and STABLE optimizers sharing the caller's objective and pipeline."""

from configuration.application_config import PipelineConfig, RestartConfig
from configuration.pipeline_factory import create_pipeline
from objective.objective_engine import ObjectiveEngine
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.local_optimizer import LocalOptimizer
from optimizer.modes.stable_optimization_config import StableOptimizationConfig
from optimizer.stable.deterministic_restart_generator import (
    DeterministicRestartGenerator,
)
from optimizer.stable.solution_selector import SolutionSelector
from optimizer.stable.stable_optimizer import StableOptimizer


def create_local_optimizer(
    config: PipelineConfig,
    objective_engine: ObjectiveEngine,
) -> LocalOptimizer:
    return LocalOptimizer(
        evaluator=MoveEvaluator(objective=objective_engine),
        pipeline=create_pipeline(config),
    )


def create_stable_optimizer(
    config: StableOptimizationConfig,
    restart: RestartConfig,
    local_optimizer: LocalOptimizer,
) -> StableOptimizer:
    return StableOptimizer(
        local_optimizer=local_optimizer,
        restart_factory=DeterministicRestartGenerator(
            separated_seed_level=restart.separated_seed_level,
            maximum_seeded_players_per_team=restart.maximum_seeded_players_per_team,
            minimum_swaps=restart.minimum_swaps,
            maximum_swaps=restart.maximum_swaps,
            partial_redistribution_ratio=restart.partial_redistribution_ratio,
        ),
        config=config,
        selector=SolutionSelector(config=config),
    )
