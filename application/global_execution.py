"""GLOBAL player adaptation, execution and verification around a STABLE warm start."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from application.balancing_request import BalancingRequest
from application.results.base_report_result import BaseReportResult
from application.results.global_report_result import GlobalReportResult
from configuration import global_factory
from configuration.application_config import ApplicationConfig
from configuration.composition_root import BalancingComposition
from objective.objective_engine import ObjectiveEngine
from optimizer.global_search.global_optimization_result import GlobalOptimizationResult
from optimizer.global_search.global_optimizer import GlobalOptimizer
from optimizer.global_search.global_search_state import GlobalPlayerMetrics
from optimizer.modes.optimization_mode import OptimizationMode
from scoring.scoring_model import ScoringModel


def get_player_attribute(
    player: Any,
    primary: str,
    alternative: str | None = None,
) -> Any:
    """
    Obtiene un atributo contemplando un nombre alternativo.
    """

    value = getattr(
        player,
        primary,
        None,
    )

    if value is None and alternative is not None:
        value = getattr(
            player,
            alternative,
            None,
        )

    return value


def get_player_nickname(
    player: Any,
) -> str:
    """
    Nick mostrado del jugador.
    """

    return str(
        get_player_attribute(
            player,
            "nickname",
            "nick",
        )
        or "Unknown"
    )


def create_global_metrics(
    players: Iterable[Any],
    scoring_model: ScoringModel,
) -> tuple[GlobalPlayerMetrics, ...]:
    metrics: list[GlobalPlayerMetrics] = []

    for player in players:
        elo = get_player_attribute(
            player,
            "elo",
            "faceit_elo",
        )

        kd = get_player_attribute(
            player,
            "kd",
        )

        seed = getattr(
            player,
            "seed",
            None,
        )

        if elo is None:
            raise ValueError(f"{get_player_nickname(player)} no contiene ELO.")

        if kd is None:
            raise ValueError(f"{get_player_nickname(player)} no contiene KD.")

        metrics.append(
            GlobalPlayerMetrics(
                player=player,
                power=float(scoring_model.power(player)),
                elo=float(elo),
                kd=float(kd),
                seed=(int(seed) if seed is not None else None),
            )
        )

    return tuple(metrics)


def run_global_optimization(
    players: Iterable[Any],
    scoring_model: ScoringModel,
    objective_engine: ObjectiveEngine,
    stable_result: BaseReportResult,
    *,
    config: ApplicationConfig,
    optimizer_factory: Callable[[ApplicationConfig, ObjectiveEngine], GlobalOptimizer]
    | None = None,
    title: str | None = None,
) -> tuple[
    GlobalReportResult,
    GlobalOptimizationResult,
]:
    """Execute and verify GLOBAL using the exact STABLE incumbent.

    The tuple, factory override and title override preserve the legacy helper
    contract. ApplicationGlobalRunner exposes only the report and uses the
    production factories and warm-start title without overrides.
    """

    problem = global_factory.create_global_problem(
        config,
        create_global_metrics(players, scoring_model),
    )
    factory = (
        optimizer_factory
        if optimizer_factory is not None
        else global_factory.create_global_optimizer
    )
    optimizer = factory(config, objective_engine)
    search_config = config.global_search

    global_result = optimizer.optimize(
        problem=problem,
        incumbent_teams=stable_result.teams,
        incumbent_score=stable_result.final_score,
    )

    # Re-evaluación final con la autoridad real del ObjectiveEngine.
    objective_result = objective_engine.evaluate(global_result.teams)

    if (
        abs(float(objective_result.score) - float(global_result.score))
        > search_config.score_tolerance
    ):
        raise RuntimeError(
            "GLOBAL devolvió un score inconsistente con "
            "ObjectiveEngine. "
            f"GLOBAL={global_result.score:.8f}, "
            f"ObjectiveEngine={objective_result.score:.8f}."
        )

    metadata = dict(
        getattr(
            stable_result,
            "metadata",
            {},
        )
    )

    metadata["optimization_applied"] = True
    metadata["optimization_mode"] = OptimizationMode.GLOBAL.value
    metadata["optimization_mode_label"] = OptimizationMode.GLOBAL.label
    metadata["optimization_deterministic"] = OptimizationMode.GLOBAL.deterministic

    metadata["global_optimization"] = {
        "initial_incumbent_score": global_result.initial_incumbent_score,
        "final_score": global_result.score,
        "improvement": global_result.improvement,
        "nodes_visited": global_result.nodes_visited,
        "complete_solutions_evaluated": global_result.complete_solutions_evaluated,
        "pruned_nodes": global_result.pruned_nodes,
        "capacity_prunes": global_result.capacity_prunes,
        "seed_prunes": global_result.seed_prunes,
        "bound_prunes": global_result.bound_prunes,
        "elapsed_seconds": global_result.elapsed_seconds,
        "optimality_proven": global_result.optimality_proven,
        "stopped_by_limit": global_result.stopped_by_limit,
        "stop_reason": global_result.stop_reason,
    }

    report_result = GlobalReportResult(
        teams=global_result.teams,
        objective_result=objective_result,
        initial_score=global_result.initial_incumbent_score,
        global_result=global_result,
        title=stable_result.title if title is None else title,
        metadata=metadata,
    )

    return (
        report_result,
        global_result,
    )


class ApplicationGlobalRunner:
    """Default GLOBAL executor; the application has already produced STABLE."""

    def run(
        self,
        *,
        request: BalancingRequest,
        composition: BalancingComposition,
        warm_start: BaseReportResult,
    ) -> BaseReportResult:
        report, _ = run_global_optimization(
            players=request.players,
            scoring_model=composition.scoring_model,
            objective_engine=composition.objective_engine,
            stable_result=warm_start,
            config=composition.config,
        )
        return report
