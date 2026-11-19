"""Legacy command and compatibility imports for its public helpers."""

from __future__ import annotations

from application.balance_console import (
    format_confidence,
    format_elapsed_seconds,
    format_restart_number,
    format_stop_reason,
    print_global_optimization,
    print_mode,
    print_objective_breakdown,
    print_players_debug,
    print_result,
    print_stable_optimization,
    print_team_debug,
)
from application.balance_validation import (
    get_player_identity,
    validate_players,
    validate_preassigned_result,
    validate_result,
    validate_same_player_collection,
    validate_teams,
)
from application.balance_workflow import BalanceWorkflow, create_run_metadata
from application.global_execution import get_player_attribute, get_player_nickname
from application.results.global_report_result import (
    GlobalReportResult,
)
from configuration.application_config import ApplicationConfig
from importers.balance_source import (
    get_faceit_api_key,
    resolve_players_file,
    run_faceit_import,
)

__all__ = [
    "GlobalReportResult",
    "create_run_metadata",
    "format_confidence",
    "format_elapsed_seconds",
    "format_restart_number",
    "format_stop_reason",
    "get_faceit_api_key",
    "get_player_attribute",
    "get_player_identity",
    "get_player_nickname",
    "main",
    "print_global_optimization",
    "print_mode",
    "print_objective_breakdown",
    "print_players_debug",
    "print_result",
    "print_stable_optimization",
    "print_team_debug",
    "resolve_players_file",
    "run_faceit_import",
    "validate_players",
    "validate_preassigned_result",
    "validate_result",
    "validate_same_player_collection",
    "validate_teams",
]


def main() -> int:
    """Run the legacy defaults and translate operator-facing failures."""
    try:
        BalanceWorkflow().run(ApplicationConfig.production_defaults())
        return 0

    except FileNotFoundError as error:
        print()
        print(f"ERROR DE ARCHIVO: {error}")

        return 1

    except (
        TypeError,
        ValueError,
        RuntimeError,
        KeyError,
        AssertionError,
    ) as error:
        print()
        print(f"ERROR: {error}")

        return 1

    except KeyboardInterrupt:
        print()
        print("Proceso cancelado por el usuario.")

        return 130


if __name__ == "__main__":
    raise SystemExit(main())
