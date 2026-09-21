"""Build balancing collaborators without running imports, search or reporting."""

from dataclasses import dataclass

from application.lan_balancer import LanBalancer
from configuration.application_config import ApplicationConfig
from configuration.objective_factory import create_objective_engine
from configuration.optimization_factory import (
    create_local_optimizer,
    create_stable_optimizer,
)
from configuration.scoring_factory import create_scoring_model
from evaluation.preassigned_team_evaluator import PreassignedTeamEvaluator
from exporters.html_v2.html_exporter import HtmlExporterV2
from generators.preassigned_team_generator import PreassignedTeamGenerator
from generators.snake_draft_generator import SnakeDraftGenerator
from importers.csstats_importer import CssStatsImporter
from objective.objective_engine import ObjectiveEngine
from optimizer.modes.optimization_mode import OptimizationMode
from scoring.scoring_model import ScoringModel


@dataclass(frozen=True, slots=True)
class BalancingComposition:
    """Shared collaborators for execution, GLOBAL construction and reporting.

    The holder is immutable; each composition owns fresh mutable collaborators.
    The local optimizer and pipeline are accessible through balancer.optimizer.
    """

    config: ApplicationConfig
    scoring_model: ScoringModel
    objective_engine: ObjectiveEngine
    balancer: LanBalancer


def create_balancing_composition(config: ApplicationConfig) -> BalancingComposition:
    """Compose a fresh production graph from the supplied configuration."""
    scoring = create_scoring_model(config.scoring)
    objective = create_objective_engine(
        config.objective,
        scoring,
        team_size=config.event.team_size,
    )
    return BalancingComposition(
        config=config,
        scoring_model=scoring,
        objective_engine=objective,
        balancer=create_balancer(config, scoring, objective),
    )


def create_balancer(
    config: ApplicationConfig,
    scoring_model: ScoringModel,
    objective_engine: ObjectiveEngine | None = None,
) -> LanBalancer:
    """Wire LanBalancer, optionally sharing an existing objective for GLOBAL."""
    if objective_engine is None:
        objective_engine = create_objective_engine(
            config.objective,
            scoring_model,
            team_size=config.event.team_size,
        )
    local_optimizer = create_local_optimizer(config.pipeline, objective_engine)
    stable_optimizer = create_stable_optimizer(
        config.stable, config.restart, local_optimizer
    )
    return LanBalancer(
        importer=CssStatsImporter(strict=config.event.importer_strict),
        generator=SnakeDraftGenerator(
            scoring_model=scoring_model,
            team_name_prefix=config.event.team_name_prefix,
            separated_seed_level=config.restart.separated_seed_level,
            maximum_seeded_players_per_team=config.restart.maximum_seeded_players_per_team,
        ),
        optimizer=local_optimizer,
        preassigned_generator=PreassignedTeamGenerator(
            expected_team_size=config.event.team_size,
            expected_player_count=config.event.expected_player_count,
            team_name_prefix=config.event.team_name_prefix,
            require_all_teams=config.event.require_all_teams,
        ),
        preassigned_evaluator=PreassignedTeamEvaluator(
            objective_engine=objective_engine,
            title=config.event.preassigned_title,
        ),
        exporter=HtmlExporterV2(
            scoring_model=scoring_model, title=config.event.report_title
        ),
        # GLOBAL remains a STABLE warm start here; application orchestrates search later.
        optimization_mode=(
            OptimizationMode.STABLE
            if config.optimization_mode is OptimizationMode.GLOBAL
            else config.optimization_mode
        ),
        stable_optimizer=stable_optimizer,
    )
