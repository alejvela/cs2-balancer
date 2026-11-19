from __future__ import annotations

from pathlib import Path
from typing import Any

from application.balance_console import (
    print_global_optimization,
    print_mode,
    print_objective_breakdown,
    print_players_debug,
    print_report_path,
    print_result,
    print_team_debug,
)
from application.balance_validation import validate_players, validate_result
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.results.base_report_result import BaseReportResult
from application.results.global_report_result import GlobalReportResult
from configuration.application_config import ApplicationConfig
from configuration.reporting_factory import create_reporting_components
from importers.balance_source import resolve_players_file
from importers.csstats_importer import CssStatsImporter
from optimizer.modes.optimization_mode import OptimizationMode


def create_run_metadata(
    players_file: Path, config: ApplicationConfig
) -> dict[str, Any]:
    """Bootstrap metadata; the result supplies the detected report mode."""
    return {
        "event_name": config.event.name,
        "source_file": str(players_file),
        "number_of_teams": config.event.number_of_teams,
        "team_size": config.event.team_size,
        "expected_player_count": config.event.expected_player_count,
        "source": "FACEIT" if config.faceit.run_import else "CSV",
    }


class BalanceWorkflow:
    """Run one configured balance and publish its reports."""

    def run(self, config: ApplicationConfig) -> BaseReportResult:
        players_file = resolve_players_file(config)
        players = CssStatsImporter(strict=config.event.importer_strict).load(
            players_file
        )
        validate_players(players, config.event.expected_player_count)
        if config.debug_players:
            print_players_debug(players)

        request = BalancingRequest(
            players=players,
            number_of_teams=config.event.number_of_teams,
            optimization_mode=config.optimization_mode,
            title=config.event.report_title,
            metadata=create_run_metadata(players_file, config),
        )
        application = BalancingApplication(config)
        result = application.run(request)
        validate_result(result, players, config)
        # Mode is determined by the application, never by bootstrap.
        result.metadata["mode"] = result.mode.value
        print_mode(result.mode, config)
        if config.debug_final_teams:
            debug_title = (
                "EQUIPOS PREASIGNADOS EVALUADOS"
                if result.evaluation_only
                else (
                    "EQUIPOS ÓPTIMOS GLOBAL"
                    if config.optimization_mode is OptimizationMode.GLOBAL
                    else "EQUIPOS OPTIMIZADOS"
                )
            )

            print_team_debug(
                teams=result.teams,
                title=debug_title,
            )

        reporting = create_reporting_components(config)
        exported_path = reporting.exporter.export(
            result=result, output=config.paths.output_report
        )
        print_result(result=result, scoring_model=reporting.scoring_model)
        if isinstance(result, GlobalReportResult):
            print_global_optimization(result)
        print_objective_breakdown(result)
        print_report_path(exported_path)
        return result
