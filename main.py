from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

from application import global_execution
from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.global_execution import get_player_attribute, get_player_nickname
from application.lan_balancer import (
    LanBalancer,
)
from application.results.base_report_result import (
    BaseReportResult,
)
from application.results.global_report_result import GlobalReportResult
from application.results.report_mode import (
    ReportMode,
)
from configuration import (
    composition_root,
    global_factory,
    objective_factory,
    pipeline_factory,
    scoring_factory,
)
from configuration.application_config import ApplicationConfig
from configuration.composition_root import BalancingComposition
from importers.csstats_importer import CssStatsImporter
from objective.objective_engine import (
    ObjectiveEngine,
)
from optimizer.global_search.global_optimization_result import (
    GlobalOptimizationResult,
)
from optimizer.global_search.global_optimizer import (
    GlobalOptimizer,
)
from optimizer.global_search.global_search_problem import (
    GlobalSearchProblem,
)
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
)
from optimizer.modes.optimization_mode import (
    OptimizationMode,
)
from optimizer.optimization_pipeline import (
    OptimizationPipeline,
)
from scoring.scoring_model import (
    ScoringModel,
)
from scrapers.csv_escraper_exporter import (
    CsvScraperExporter,
)
from scrapers.faceit.faceit_api_client import (
    FaceitApiClient,
)
from scrapers.faceit.faceit_player_record_map import (
    FaceitPlayerRecordMapper,
)
from scrapers.faceit.faceit_scrapper import (
    FaceitScraper,
)

APPLICATION_CONFIG = ApplicationConfig.production_defaults()

# Compatibility aliases for SCRUM-37; factories receive explicit config snapshots.
SOURCE_PLAYERS_FILE = APPLICATION_CONFIG.paths.source_players
GENERATED_STATS_FILE = APPLICATION_CONFIG.paths.generated_stats
FACEIT_ERRORS_FILE = APPLICATION_CONFIG.paths.faceit_errors
OUTPUT_REPORT_FILE = APPLICATION_CONFIG.paths.output_report
NUMBER_OF_TEAMS = APPLICATION_CONFIG.event.number_of_teams
TEAM_SIZE = APPLICATION_CONFIG.event.team_size
EXPECTED_PLAYER_COUNT = APPLICATION_CONFIG.event.expected_player_count
EVENT_NAME = APPLICATION_CONFIG.event.name
REPORT_TITLE = APPLICATION_CONFIG.event.report_title
RUN_FACEIT_IMPORT = APPLICATION_CONFIG.faceit.run_import
DEBUG_PLAYERS = APPLICATION_CONFIG.debug_players
DEBUG_FINAL_TEAMS = APPLICATION_CONFIG.debug_final_teams
OPTIMIZATION_MODE = APPLICATION_CONFIG.optimization_mode
STABLE_OPTIMIZATION_CONFIG = APPLICATION_CONFIG.stable
GLOBAL_OPTIMIZATION_CONFIG = APPLICATION_CONFIG.global_search
FACEIT_PREFERRED_GAME_ID = APPLICATION_CONFIG.faceit.preferred_game_id
FACEIT_FALLBACK_GAME_IDS = APPLICATION_CONFIG.faceit.fallback_game_ids
FACEIT_RECENT_MATCHES = APPLICATION_CONFIG.faceit.recent_matches
FACEIT_STRICT = APPLICATION_CONFIG.faceit.strict
FACEIT_DELAY_SECONDS = APPLICATION_CONFIG.faceit.delay_seconds
FACEIT_TIMEOUT_SECONDS = APPLICATION_CONFIG.faceit.timeout_seconds
FACEIT_RETRIES = APPLICATION_CONFIG.faceit.retries
FACEIT_RETRY_DELAY_SECONDS = APPLICATION_CONFIG.faceit.retry_delay_seconds


def _composition_config() -> ApplicationConfig:
    """Translate legacy aliases at the entrypoint boundary only."""
    return replace(
        APPLICATION_CONFIG,
        event=replace(
            APPLICATION_CONFIG.event,
            number_of_teams=NUMBER_OF_TEAMS,
            team_size=TEAM_SIZE,
            report_title=REPORT_TITLE,
        ),
        stable=STABLE_OPTIMIZATION_CONFIG,
        global_search=GLOBAL_OPTIMIZATION_CONFIG,
        optimization_mode=OPTIMIZATION_MODE,
    )


# ============================================================
# Scoring individual
# ============================================================

def create_scoring_model() -> ScoringModel:
    return scoring_factory.create_scoring_model(APPLICATION_CONFIG.scoring)


# ============================================================
# Objective Engine
# ============================================================

def create_objective_engine(scoring_model: ScoringModel) -> ObjectiveEngine:
    return objective_factory.create_objective_engine(
        APPLICATION_CONFIG.objective, scoring_model, team_size=TEAM_SIZE,
    )


# ============================================================
# Pipeline de optimización
# ============================================================

def create_pipeline() -> OptimizationPipeline:
    return pipeline_factory.create_pipeline(APPLICATION_CONFIG.pipeline)


# ============================================================
# Construcción de la aplicación
# ============================================================

def create_balancer(
    scoring_model: ScoringModel,
    objective_engine: ObjectiveEngine | None = None,
) -> LanBalancer:
    return composition_root.create_balancer(
        _composition_config(), scoring_model, objective_engine,
    )


# ============================================================
# GLOBAL - construcción del problema
# ============================================================

def create_global_metrics(
    players: Iterable[Any], scoring_model: ScoringModel,
) -> tuple[GlobalPlayerMetrics, ...]:
    """Compatibility-only forwarding wrapper; implementation lives in application."""
    return global_execution.create_global_metrics(players, scoring_model)


def create_global_problem(
    players: Iterable[Any],
    scoring_model: ScoringModel,
) -> GlobalSearchProblem:
    return global_factory.create_global_problem(
        _composition_config(), create_global_metrics(players, scoring_model),
    )


def create_global_optimizer(objective_engine: ObjectiveEngine) -> GlobalOptimizer:
    return global_factory.create_global_optimizer(_composition_config(), objective_engine)


def run_global_optimization(
    players: Iterable[Any],
    scoring_model: ScoringModel,
    objective_engine: ObjectiveEngine,
    stable_result: BaseReportResult,
    *,
    config: ApplicationConfig | None = None,
) -> tuple[GlobalReportResult, GlobalOptimizationResult]:
    """Compatibility-only: preserve SCRUM-37 overrides and its tuple return."""
    return global_execution.run_global_optimization(
        players, scoring_model, objective_engine, stable_result,
        config=config if config is not None else _composition_config(),
        optimizer_factory=(
            (lambda config, objective: create_global_optimizer(objective_engine=objective))
            if config is None else None
        ),
        title=REPORT_TITLE if config is None else stable_result.title,
    )


def print_global_optimization(
    result: GlobalReportResult,
) -> None:
    print()
    print("=" * 72)
    print("OPTIMIZACIÓN GLOBAL")
    print("=" * 72)

    print(
        f"Incumbent inicial:      "
        f"{result.initial_incumbent_score:.4f}"
    )

    print(
        f"Score final:            "
        f"{result.score:.4f}"
    )

    print(
        f"Mejora GLOBAL:          "
        f"{result.improvement:+.4f}"
    )

    print(
        f"Nodos explorados:       "
        f"{result.nodes_visited:,}"
    )

    print(
        f"Soluciones evaluadas:   "
        f"{result.complete_solutions_evaluated:,}"
    )

    print(
        f"Ramas podadas:          "
        f"{result.pruned_nodes:,}"
    )

    print(
        f"  Capacidad:            "
        f"{result.capacity_prunes:,}"
    )

    print(
        f"  Seeds:                "
        f"{result.seed_prunes:,}"
    )

    print(
        f"  Bound / Power:        "
        f"{result.bound_prunes:,}"
    )

    print(
        f"Tiempo GLOBAL:          "
        f"{format_elapsed_seconds(result.elapsed_seconds)}"
    )

    print(
        f"Límite alcanzado:       "
        f"{'SÍ' if result.stopped_by_limit else 'NO'}"
    )

    print(
        f"Espacio agotado:        "
        f"{'SÍ' if result.stop_reason == 'SEARCH_EXHAUSTED' else 'NO'}"
    )

    print(
        f"Óptimo demostrado:      "
        f"{'SÍ' if result.optimality_proven else 'NO'}"
    )

    print(
        f"Motivo de parada:       "
        f"{result.stop_reason}"
    )


# ============================================================
# FACEIT API key
# ============================================================

def get_faceit_api_key() -> str:
    """
    Obtiene la API key de FACEIT desde la variable de entorno
    FACEIT_API_KEY.
    """

    api_key = os.environ.get(
        "FACEIT_API_KEY"
    )

    if api_key is None:
        raise RuntimeError(
            "La variable de entorno FACEIT_API_KEY "
            "no está definida."
        )

    normalized = api_key.strip()

    if not normalized:
        raise RuntimeError(
            "La variable de entorno FACEIT_API_KEY "
            "está vacía."
        )

    return normalized


# ============================================================
# Importación FACEIT
# ============================================================

def run_faceit_import() -> Path:
    """
    Consulta FACEIT para todos los jugadores del CSV inicial.

    El CSV de entrada contiene la configuración manual:

        Nick
        FaceitNickname
        Seed
        Team

    El scraper y CsvScraperExporter deben conservar Seed y Team
    durante todo el proceso para que el CSV generado pueda utilizarse
    posteriormente tanto en modo automático como preasignado.
    """

    if not SOURCE_PLAYERS_FILE.exists():
        raise FileNotFoundError(
            "No existe el archivo de entrada: "
            f"{SOURCE_PLAYERS_FILE.resolve()}"
        )

    api_key = get_faceit_api_key()

    print()
    print("=" * 72)
    print(
        "IMPORTACIÓN DE JUGADORES DESDE FACEIT"
    )
    print("=" * 72)

    print(
        f"Entrada:              "
        f"{SOURCE_PLAYERS_FILE}"
    )

    print(
        f"Juego preferido:      "
        f"{FACEIT_PREFERRED_GAME_ID}"
    )

    print(
        "Juegos fallback:      "
        f"{', '.join(FACEIT_FALLBACK_GAME_IDS)}"
    )

    print(
        f"Partidas recientes:   "
        f"{FACEIT_RECENT_MATCHES}"
    )

    print()

    with FaceitApiClient(
        api_key=api_key,
        preferred_game_id=(
            FACEIT_PREFERRED_GAME_ID
        ),
        fallback_game_ids=(
            FACEIT_FALLBACK_GAME_IDS
        ),
        timeout=FACEIT_TIMEOUT_SECONDS,
        retries=FACEIT_RETRIES,
        retry_delay=(
            FACEIT_RETRY_DELAY_SECONDS
        ),
    ) as client:

        mapper = FaceitPlayerRecordMapper(
            game_id=FACEIT_PREFERRED_GAME_ID,
            source_name="FACEIT",
        )

        scraper = FaceitScraper(
            client=client,
            mapper=mapper,
            recent_matches=FACEIT_RECENT_MATCHES,
            strict=FACEIT_STRICT,
            delay=FACEIT_DELAY_SECONDS,
            maximum_seed_one_players=(
                NUMBER_OF_TEAMS
            ),
        )

        records = scraper.scrape(
            SOURCE_PLAYERS_FILE
        )

        scraper_errors = (
            scraper.errors
        )

    valid_records = [
        record
        for record in records
        if record.is_valid
    ]

    failed_records = [
        record
        for record in records
        if not record.is_valid
    ]

    print(
        f"Jugadores esperados:  "
        f"{EXPECTED_PLAYER_COUNT}"
    )

    print(
        f"Jugadores válidos:    "
        f"{len(valid_records)}"
    )

    print(
        f"Jugadores con error:  "
        f"{len(failed_records)}"
    )

    if failed_records:
        print()
        print(
            "JUGADORES CON ERROR"
        )
        print("-" * 72)

        for record in failed_records:
            print(
                f"- {record.nickname}: "
                f"{record.error or 'Error desconocido'}"
            )

        CsvScraperExporter(
            include_errors=True,
        ).export(
            records=failed_records,
            output=FACEIT_ERRORS_FILE,
        )

        print()

        print(
            "Errores guardados en: "
            f"{FACEIT_ERRORS_FILE.resolve()}"
        )

    if scraper_errors:
        print()
        print(
            "DETALLE TÉCNICO"
        )
        print("-" * 72)

        for error in scraper_errors:
            print(
                f"Fila {error.get('row')}: "
                f"{error.get('nick')} / "
                f"{error.get('faceit_nickname')} -> "
                f"{error.get('error')}"
            )

    if (
        len(valid_records)
        != EXPECTED_PLAYER_COUNT
    ):
        raise RuntimeError(
            "El número de jugadores válidos no coincide "
            "con el esperado. "
            f"Esperados: {EXPECTED_PLAYER_COUNT}. "
            f"Obtenidos: {len(valid_records)}."
        )

    generated_file = CsvScraperExporter(
        include_errors=False,
    ).export(
        records=valid_records,
        output=GENERATED_STATS_FILE,
    )

    print()

    print(
        "CSV de estadísticas generado: "
        f"{generated_file.resolve()}"
    )

    return generated_file


def resolve_players_file() -> Path:
    """
    Devuelve el CSV que debe utilizar la aplicación.

    Cuando RUN_FACEIT_IMPORT=True se regeneran primero las
    estadísticas.

    Cuando es False se reutiliza players_stats.csv.
    """

    if RUN_FACEIT_IMPORT:
        return run_faceit_import()

    if not GENERATED_STATS_FILE.exists():
        raise FileNotFoundError(
            "No existe el archivo generado: "
            f"{GENERATED_STATS_FILE.resolve()}"
        )

    return GENERATED_STATS_FILE


# ============================================================
# Identidad de jugadores
# ============================================================


def get_player_identity(
    player: Any,
) -> str:
    """
    Construye una identidad estable.

    Prioridad:

        1. player.identity
        2. Steam ID
        3. nickname
    """

    identity = getattr(
        player,
        "identity",
        None,
    )

    if identity:
        return (
            str(identity)
            .strip()
            .casefold()
        )

    steam_id = get_player_attribute(
        player,
        "steam_id",
    )

    if steam_id:
        return (
            "steam:"
            f"{str(steam_id).strip().casefold()}"
        )

    nickname = get_player_nickname(
        player
    )

    return (
        "nick:"
        f"{nickname.strip().casefold()}"
    )


# ============================================================
# Validación de jugadores de entrada
# ============================================================

def validate_players(
    players: Iterable[Any],
    expected_player_count: int,
) -> None:
    """
    Verifica la colección de jugadores antes de ejecutar el
    balanceador.
    """

    player_list = list(
        players
    )

    if (
        len(player_list)
        != expected_player_count
    ):
        raise RuntimeError(
            f"Se han importado {len(player_list)} jugadores. "
            f"Se esperaban {expected_player_count}."
        )

    object_ids = [
        id(player)
        for player in player_list
    ]

    if (
        len(object_ids)
        != len(set(object_ids))
    ):
        raise RuntimeError(
            "La colección de entrada contiene instancias "
            "de Player duplicadas."
        )

    identities = [
        get_player_identity(
            player
        )
        for player in player_list
    ]

    duplicated = [
        identity
        for identity, count
        in Counter(
            identities
        ).items()
        if count > 1
    ]

    if duplicated:
        raise RuntimeError(
            "La colección de entrada contiene jugadores "
            "duplicados: "
            f"{duplicated}."
        )


# ============================================================
# Validación estructural de equipos
# ============================================================

def validate_teams(
    teams: Iterable[Any],
    expected_team_size: int,
    expected_player_count: int,
    stage: str,
) -> None:
    """
    Comprueba:

        - Número de equipos.
        - Tamaño de cada equipo.
        - Número total de jugadores.
        - Instancias duplicadas.
        - Identidades duplicadas.
    """

    team_list = list(
        teams
    )

    if (
        len(team_list)
        != NUMBER_OF_TEAMS
    ):
        raise RuntimeError(
            f"[{stage}] Se esperaban "
            f"{NUMBER_OF_TEAMS} equipos, "
            f"pero existen {len(team_list)}."
        )

    object_locations: dict[
        int,
        list[str],
    ] = {}

    identity_locations: dict[
        str,
        list[str],
    ] = {}

    total_players = 0

    for team_index, team in enumerate(
        team_list,
        start=1,
    ):
        team_name = (
            getattr(
                team,
                "name",
                None,
            )
            or f"Equipo {team_index}"
        )

        players = list(
            getattr(
                team,
                "players",
                (),
            )
        )

        if (
            len(players)
            != expected_team_size
        ):
            raise RuntimeError(
                f"[{stage}] {team_name} contiene "
                f"{len(players)} jugadores. "
                f"Se esperaban {expected_team_size}."
            )

        total_players += len(
            players
        )

        for player_index, player in enumerate(
            players,
            start=1,
        ):
            location = (
                f"{team_name}[{player_index}]"
            )

            object_locations.setdefault(
                id(player),
                [],
            ).append(
                location
            )

            identity_locations.setdefault(
                get_player_identity(
                    player
                ),
                [],
            ).append(
                location
            )

    if (
        total_players
        != expected_player_count
    ):
        raise RuntimeError(
            f"[{stage}] Existen "
            f"{total_players} posiciones de jugadores. "
            f"Se esperaban {expected_player_count}."
        )

    duplicated_objects = {
        object_id: locations
        for object_id, locations
        in object_locations.items()
        if len(locations) > 1
    }

    duplicated_identities = {
        identity: locations
        for identity, locations
        in identity_locations.items()
        if len(locations) > 1
    }

    if duplicated_objects:
        details = "; ".join(
            (
                f"object_id={object_id}: "
                f"{', '.join(locations)}"
            )
            for object_id, locations
            in duplicated_objects.items()
        )

        raise RuntimeError(
            f"[{stage}] Se han detectado instancias "
            f"de Player repetidas. {details}"
        )

    if duplicated_identities:
        details = "; ".join(
            (
                f"{identity}: "
                f"{', '.join(locations)}"
            )
            for identity, locations
            in duplicated_identities.items()
        )

        raise RuntimeError(
            f"[{stage}] Se han detectado jugadores "
            f"duplicados por identidad. {details}"
        )


def validate_same_player_collection(
    players_before: Iterable[Any],
    teams_after: Iterable[Any],
) -> None:
    """
    Garantiza que el proceso conserva exactamente la misma
    colección lógica de jugadores.
    """

    before_counter = Counter(
        get_player_identity(
            player
        )
        for player in players_before
    )

    after_counter = Counter(
        get_player_identity(
            player
        )
        for team in teams_after
        for player in team.players
    )

    if (
        before_counter
        == after_counter
    ):
        return

    missing = (
        before_counter
        - after_counter
    )

    unexpected = (
        after_counter
        - before_counter
    )

    raise RuntimeError(
        "El proceso ha modificado la colección de jugadores. "
        f"Ausentes: {dict(missing)}. "
        f"Inesperados: {dict(unexpected)}."
    )


# ============================================================
# Validación específica por modo
# ============================================================

def validate_result(
    result: BaseReportResult,
    players: Iterable[Any],
) -> None:
    """
    Ejecuta las validaciones comunes y específicas del modo.
    """

    if not isinstance(
        result,
        BaseReportResult,
    ):
        raise TypeError(
            "result must be a BaseReportResult instance."
        )

    validate_teams(
        teams=result.teams,
        expected_team_size=TEAM_SIZE,
        expected_player_count=(
            EXPECTED_PLAYER_COUNT
        ),
        stage="Resultado",
    )

    validate_same_player_collection(
        players_before=players,
        teams_after=result.teams,
    )

    if (
        result.mode
        is ReportMode.OPTIMIZED
    ):
        if (
            result.final_score
            < result.initial_score
        ):
            raise RuntimeError(
                "La optimización ha terminado con una "
                "puntuación inferior a la inicial. "
                f"Inicial: {result.initial_score:.2f}. "
                f"Final: {result.final_score:.2f}."
            )

    elif (
        result.mode
        is ReportMode.PREASSIGNED
    ):
        validate_preassigned_result(
            result
        )


def validate_preassigned_result(
    result: BaseReportResult,
) -> None:
    """
    Comprueba que la composición final coincide con los Team
    indicados en cada Player.
    """

    errors: list[str] = []

    for team_index, team in enumerate(
        result.teams,
        start=1,
    ):
        team_id = getattr(
            team,
            "id",
            team_index,
        )

        for player in team.players:
            assigned_team = getattr(
                player,
                "team_number",
                getattr(
                    player,
                    "assigned_team_number",
                    None,
                ),
            )

            if assigned_team is None:
                errors.append(
                    f"{get_player_nickname(player)} "
                    "no contiene Team."
                )

                continue

            try:
                assigned_team_value = int(
                    assigned_team
                )

            except (
                TypeError,
                ValueError,
            ):
                errors.append(
                    f"{get_player_nickname(player)} "
                    f"contiene Team={assigned_team!r}."
                )

                continue

            try:
                actual_team_value = int(
                    team_id
                )

            except (
                TypeError,
                ValueError,
            ):
                actual_team_value = (
                    team_index
                )

            if (
                assigned_team_value
                != actual_team_value
            ):
                errors.append(
                    f"{get_player_nickname(player)} "
                    f"tiene Team={assigned_team_value}, "
                    f"pero aparece en "
                    f"Equipo {actual_team_value}."
                )

    if errors:
        raise RuntimeError(
            "La evaluación preasignada no ha conservado "
            "correctamente los equipos: "
            + " | ".join(errors)
        )


# ============================================================
# Información del modo
# ============================================================

def print_mode(
    mode: ReportMode,
) -> None:
    """
    Muestra por consola qué flujo va a ejecutarse.
    """

    print()
    print("=" * 72)
    print(
        "MODO DE EJECUCIÓN"
    )
    print("=" * 72)

    print(
        f"Modo:                 "
        f"{mode.value}"
    )

    print(
        f"Descripción:          "
        f"{mode.label}"
    )

    if mode is ReportMode.PREASSIGNED:
        print(
            "Acción:               "
            "Evaluar equipos del CSV"
        )

        print(
            "Optimización:         "
            "NO"
        )

    else:
        print(
            "Acción:               "
            "Generar y optimizar equipos"
        )

        print(
            "Optimización:         "
            "SÍ"
        )

        print(
            "Motor:                "
            f"{OPTIMIZATION_MODE.value.upper()}"
        )


# ============================================================
# Depuración de jugadores
# ============================================================

def print_players_debug(
    players: Iterable[Any],
) -> None:
    """
    Muestra los datos básicos importados.
    """

    print()
    print("=" * 72)
    print(
        "JUGADORES IMPORTADOS"
    )
    print("=" * 72)

    for index, player in enumerate(
        players,
        start=1,
    ):
        nickname = get_player_nickname(
            player
        )

        team_number = getattr(
            player,
            "team_number",
            None,
        )

        seed = getattr(
            player,
            "seed",
            None,
        )

        print(
            f"[{index:02d}] "
            f"{nickname:<20} "
            f"| Team: "
            f"{str(team_number or '—'):<3} "
            f"| Seed: "
            f"{str(seed or '—'):<3} "
            f"| identity="
            f"{get_player_identity(player)!r}"
        )


# ============================================================
# Depuración de equipos
# ============================================================

def print_team_debug(
    teams: Iterable[Any],
    title: str,
) -> None:
    """
    Muestra la composición de los equipos.
    """

    print()
    print("=" * 72)
    print(
        title
    )
    print("=" * 72)

    for team_index, team in enumerate(
        teams,
        start=1,
    ):
        team_name = (
            getattr(
                team,
                "name",
                None,
            )
            or f"Equipo {team_index}"
        )

        print()
        print(
            str(team_name).upper()
        )
        print("-" * 72)

        for player_index, player in enumerate(
            team.players,
            start=1,
        ):
            nickname = get_player_nickname(
                player
            )

            assigned_team = getattr(
                player,
                "team_number",
                None,
            )

            print(
                f"[{player_index}] "
                f"{nickname:<20} "
                f"| Team CSV: "
                f"{str(assigned_team or '—'):<3} "
                f"| identity="
                f"{get_player_identity(player)!r}"
            )


# ============================================================
# Diagnóstico STABLE
# ============================================================

def format_confidence(
    value: Any,
) -> str:
    normalized = (
        str(value or "UNKNOWN")
        .strip()
        .upper()
    )

    labels = {
        "NONE": "SIN DATOS",
        "LOW": "BAJA",
        "MEDIUM": "MEDIA",
        "HIGH": "ALTA",
        "VERY_HIGH": "MUY ALTA",
        "UNKNOWN": "DESCONOCIDA",
    }

    return labels.get(
        normalized,
        normalized.replace(
            "_",
            " ",
        ),
    )


def format_stop_reason(
    value: Any,
) -> str:
    if value is None:
        return "DESCONOCIDO"

    normalized = (
        str(value)
        .strip()
        .casefold()
    )

    labels = {
        "perfect_score": "PUNTUACIÓN PERFECTA",
        "target_confirmed": "TARGET CONFIRMADO",
        "convergence": "CONVERGENCIA",
        "restart_limit": "LÍMITE DE RESTARTS",
        "evaluation_limit": "LÍMITE DE EVALUACIONES",
        "elapsed_limit": "LÍMITE DE TIEMPO",
    }

    return labels.get(
        normalized,
        normalized.upper().replace(
            "_",
            " ",
        ),
    )


def format_restart_number(
    value: Any,
) -> str:
    if value is None:
        return "—"

    try:
        return str(
            int(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"


def format_elapsed_seconds(
    value: Any,
) -> str:
    try:
        seconds = max(
            0.0,
            float(value),
        )
    except (
        TypeError,
        ValueError,
    ):
        return "—"

    if seconds < 1.0:
        return (
            f"{seconds * 1000.0:.2f} ms"
        )

    if seconds < 60.0:
        return (
            f"{seconds:.2f} s"
        )

    minutes = int(
        seconds // 60.0
    )

    remaining_seconds = (
        seconds
        - minutes * 60.0
    )

    return (
        f"{minutes} min "
        f"{remaining_seconds:.1f} s"
    )


def print_stable_optimization(
    result: BaseReportResult,
) -> None:
    metadata = getattr(
        result,
        "metadata",
        {},
    )

    if not isinstance(
        metadata,
        dict,
    ):
        return

    stable_data = metadata.get(
        "stable_optimization"
    )

    if not isinstance(
        stable_data,
        dict,
    ):
        return

    convergence = stable_data.get(
        "convergence",
        {},
    )

    if not isinstance(
        convergence,
        dict,
    ):
        convergence = {}

    signature = stable_data.get(
        "signature",
        {},
    )

    if not isinstance(
        signature,
        dict,
    ):
        signature = {}

    print()
    print("=" * 72)
    print("OPTIMIZACIÓN ESTABLE")
    print("=" * 72)

    score = stable_data.get(
        "score"
    )

    if score is not None:
        print(
            f"Score seleccionado:    "
            f"{float(score):.4f}"
        )

    penalty = stable_data.get(
        "penalty"
    )

    if penalty is not None:
        print(
            f"Penalización:          "
            f"{float(penalty):.2f}"
        )

    print(
        f"Confianza:             "
        f"{format_confidence(stable_data.get('confidence'))}"
    )

    print(
        f"Restarts completados:  "
        f"{stable_data.get('completed_restarts', 0)}"
    )

    print(
        f"Soluciones únicas:     "
        f"{stable_data.get('unique_solutions', 0)}"
    )

    print(
        f"Mejor encontrada en:   "
        f"{format_restart_number(stable_data.get('best_restart_number'))}"
    )

    print(
        f"Sin mejora:            "
        f"{convergence.get('restarts_without_improvement', 0)}"
    )

    print(
        f"Mejoras reales:        "
        f"{stable_data.get('quality_improvements', 0)}"
    )

    print(
        f"Cambios selección:     "
        f"{stable_data.get('selection_changes', 0)}"
    )

    print(
        f"Evaluaciones globales: "
        f"{convergence.get('total_evaluations', 0)}"
    )

    print(
        f"Target alcanzado:      "
        f"{'SÍ' if stable_data.get('target_reached', False) else 'NO'}"
    )

    print(
        f"Target confirmado:     "
        f"{'SÍ' if stable_data.get('target_confirmed', False) else 'NO'}"
    )

    print(
        f"Motivo de parada:      "
        f"{format_stop_reason(stable_data.get('stop_reason'))}"
    )

    print(
        f"Tiempo total STABLE:   "
        f"{format_elapsed_seconds(stable_data.get('elapsed_seconds', 0.0))}"
    )

    signature_hash = signature.get(
        "hash"
    )

    if signature_hash:
        print(
            f"Firma solución:        "
            f"{signature_hash}"
        )


def print_objective_breakdown(
    result: BaseReportResult,
) -> None:
    restrictions = getattr(
        result,
        "restrictions",
        {},
    )

    print()
    print("=" * 72)
    print("DESGLOSE DEL OBJECTIVE ENGINE")
    print("=" * 72)

    if not restrictions:
        print(
            "No hay restricciones disponibles."
        )
        return

    if isinstance(
        restrictions,
        dict,
    ):
        items = tuple(
            restrictions.items()
        )
    else:
        items = tuple(
            (
                getattr(
                    restriction,
                    "name",
                    "Unknown",
                ),
                restriction,
            )
            for restriction in restrictions
        )

    total_weighted = 0.0
    total_weight = 0.0
    total_penalty = 0.0

    for name, restriction in items:
        score = float(
            getattr(
                restriction,
                "score",
                0.0,
            )
        )

        weight = float(
            getattr(
                restriction,
                "weight",
                0.0,
            )
        )

        penalty = float(
            getattr(
                restriction,
                "penalty",
                0.0,
            )
        )

        weighted_score = (
            score
            * weight
        )

        contribution = (
            weighted_score
            / 100.0
        )

        total_weighted += weighted_score
        total_weight += weight
        total_penalty += penalty

        print(
            f"{str(name):<24}"
            f"| Score: {score:7.2f} "
            f"| Peso: {weight:6.2f} "
            f"| Aporta: {contribution:6.2f} "
            f"| Penalty: {penalty:6.2f}"
        )

    print("-" * 72)

    weighted_average = (
        total_weighted
        / total_weight
        if total_weight > 0.0
        else 0.0
    )

    print(
        f"{'MEDIA PONDERADA':<24}"
        f"| {weighted_average:7.2f}"
    )

    print(
        f"{'PENALIZACIÓN TOTAL':<24}"
        f"| {total_penalty:7.2f}"
    )

    print(
        f"{'SCORE FINAL':<24}"
        f"| {result.final_score:7.2f}"
    )


# ============================================================
# Resultado por consola
# ============================================================

def print_result(
    result: BaseReportResult,
    scoring_model: ScoringModel,
) -> None:
    """
    Muestra un resumen completo compatible con ambos modos.
    """

    print()
    print("=" * 72)
    print(
        "LAN CS2 TEAM BALANCER"
    )
    print("=" * 72)

    print(
        f"Modo:                 "
        f"{result.mode.label}"
    )

    if result.optimized:
        print(
            f"Puntuación inicial:   "
            f"{result.initial_score:.2f}"
        )

        print(
            f"Puntuación final:     "
            f"{result.final_score:.2f}"
        )

        print(
            f"Mejora total:         "
            f"{result.improvement:+.2f}"
        )

        print(
            f"Movimientos:          "
            f"{result.iterations}"
        )

        print(
            f"Evaluaciones:         "
            f"{result.total_evaluations}"
        )

        print(
            f"Tiempo optimización:  "
            f"{result.elapsed_ms:.2f} ms"
        )

        optimization_mode = (
            getattr(
                result,
                "metadata",
                {},
            )
            .get(
                "optimization_mode"
            )
        )

        print(
            f"Motor optimización:   "
            f"{str(optimization_mode or 'fast').upper()}"
        )

    else:
        print(
            f"Puntuación equilibrio:"
            f" {result.final_score:.2f}"
        )

        print(
            f"Clasificación:        "
            f"{result.balance_label}"
        )

        print(
            f"Evaluaciones:         "
            f"{result.total_evaluations}"
        )

        print(
            f"Tiempo evaluación:    "
            f"{result.elapsed_ms:.2f} ms"
        )

    print(
        f"Penalización:         "
        f"{result.penalty:.2f}"
    )

    print(
        f"Composición válida:   "
        f"{'SÍ' if result.is_valid else 'NO'}"
    )

    print(
        f"Equipos:              "
        f"{result.team_count}"
    )

    print(
        f"Jugadores:            "
        f"{result.player_count}"
    )

    if (
        result.optimized
        and getattr(
            result,
            "metadata",
            {},
        ).get(
            "optimization_mode"
        ) == OptimizationMode.STABLE.value
    ):
        print_stable_optimization(
            result
        )

    for team_index, team in enumerate(
        result.teams,
        start=1,
    ):
        team_name = (
            getattr(
                team,
                "name",
                None,
            )
            or f"Equipo {team_index}"
        )

        print()
        print("-" * 72)
        print(
            str(team_name).upper()
        )
        print("-" * 72)

        team_powers: list[float] = []

        for player in team.players:
            nickname = get_player_nickname(
                player
            )

            elo = get_player_attribute(
                player,
                "elo",
                "faceit_elo",
            )

            level = get_player_attribute(
                player,
                "faceit_level",
                "level",
            )

            kd = get_player_attribute(
                player,
                "kd",
            )

            adr = get_player_attribute(
                player,
                "adr",
            )

            team_number = getattr(
                player,
                "team_number",
                None,
            )

            power = scoring_model.power(
                player
            )

            team_powers.append(
                power
            )

            elo_text = (
                str(
                    int(
                        float(elo)
                    )
                )
                if elo is not None
                else "N/A"
            )

            level_text = (
                str(
                    int(
                        float(level)
                    )
                )
                if level is not None
                else "N/A"
            )

            kd_text = (
                f"{float(kd):.2f}"
                if kd is not None
                else "N/A"
            )

            adr_text = (
                f"{float(adr):.1f}"
                if adr is not None
                else "N/A"
            )

            team_text = (
                str(team_number)
                if team_number is not None
                else "—"
            )

            print(
                f"  {nickname:<20}"
                f"| Power: {power:6.2f} "
                f"| ELO: {elo_text:<5} "
                f"| LVL: {level_text:<3} "
                f"| KD: {kd_text:<5} "
                f"| ADR: {adr_text:<5} "
                f"| Team: {team_text}"
            )

        average_power = (
            sum(team_powers)
            / len(team_powers)
            if team_powers
            else 0.0
        )

        print(
            f"  {'':20}"
            f"| Power medio: "
            f"{average_power:.2f}"
        )

    print()


# ============================================================
# Metadata
# ============================================================

def create_run_metadata(
    players_file: Path,
    mode: ReportMode,
) -> dict[str, Any]:
    """
    Metadata básica que acompaña al resultado.

    Más adelante esta estructura podrá incluir identificador
    de evento, usuario, versión del algoritmo, configuración, etc.
    """

    return {
        "event_name": EVENT_NAME,

        "source_file": str(
            players_file
        ),

        "number_of_teams": (
            NUMBER_OF_TEAMS
        ),

        "team_size": (
            TEAM_SIZE
        ),

        "expected_player_count": (
            EXPECTED_PLAYER_COUNT
        ),

        "mode": mode.value,

        "optimization_mode": (
            OPTIMIZATION_MODE.value
            if mode is ReportMode.OPTIMIZED
            else None
        ),

        "source": (
            "FACEIT"
            if RUN_FACEIT_IMPORT
            else "CSV"
        ),
    }


# ============================================================
# Main
# ============================================================

def main() -> int:
    """
    Punto de entrada principal.

    Flujo:

        1. Obtiene/actualiza estadísticas FACEIT.
        2. Importa Player[].
        3. Detecta el modo mediante Team.
        4. Ejecuta BalancingApplication.run().
        5. GLOBAL se ejecuta completamente en application.
        6. Valida el resultado final.
        7. Genera el informe HTML.

    La diferencia clave respecto al main anterior es que ya no
    construye ni optimiza equipos directamente.

    Toda esa responsabilidad pertenece a LanBalancer.
    """

    try:
        # ----------------------------------------------------
        # CSV de estadísticas
        # ----------------------------------------------------

        players_file = (
            resolve_players_file()
        )

        # ----------------------------------------------------
        # Aplicación
        # ----------------------------------------------------

        config = _composition_config()
        composition: BalancingComposition | None = None

        def compose_run(run_config: ApplicationConfig) -> BalancingComposition:
            # Keep the run's exact scoring/export collaborators at the entrypoint.
            nonlocal composition
            composition = composition_root.create_balancing_composition(run_config)
            return composition

        application = BalancingApplication(
            config, composition_factory=compose_run,
        )
        players = CssStatsImporter(strict=config.event.importer_strict).load(players_file)

        validate_players(
            players=players,
            expected_player_count=(
                EXPECTED_PLAYER_COUNT
            ),
        )

        if DEBUG_PLAYERS:
            print_players_debug(
                players
            )

        # ----------------------------------------------------
        # Detección del modo
        # ----------------------------------------------------

        mode = LanBalancer.detect_mode(
            players
        )

        print_mode(
            mode
        )

        # ----------------------------------------------------
        # Ejecución
        # ----------------------------------------------------

        result = application.run(
            BalancingRequest(
                players=players,
                number_of_teams=NUMBER_OF_TEAMS,
                optimization_mode=OPTIMIZATION_MODE,
                title=REPORT_TITLE,
                metadata=create_run_metadata(players_file=players_file, mode=mode),
            )
        )
        assert composition is not None
        scoring_model = composition.scoring_model
        balancer = composition.balancer

        # ----------------------------------------------------
        # Validación
        # ----------------------------------------------------

        validate_result(
            result=result,
            players=players,
        )

        if DEBUG_FINAL_TEAMS:
            debug_title = (
                "EQUIPOS PREASIGNADOS EVALUADOS"
                if result.evaluation_only
                else (
                    "EQUIPOS ÓPTIMOS GLOBAL"
                    if OPTIMIZATION_MODE
                    is OptimizationMode.GLOBAL
                    else "EQUIPOS OPTIMIZADOS"
                )
            )

            print_team_debug(
                teams=result.teams,
                title=debug_title,
            )

        # ----------------------------------------------------
        # Exportación
        # ----------------------------------------------------

        exported_path = balancer.export(
            result=result,
            output=OUTPUT_REPORT_FILE,
        )

        # ----------------------------------------------------
        # Consola
        # ----------------------------------------------------

        print_result(
            result=result,
            scoring_model=scoring_model,
        )

        if isinstance(result, GlobalReportResult):
            print_global_optimization(result)

        print_objective_breakdown(
            result
        )

        print()

        print(
            "Informe HTML generado en: "
            f"{exported_path.resolve()}"
        )

        return 0

    except FileNotFoundError as error:
        print()
        print(
            f"ERROR DE ARCHIVO: {error}"
        )

        return 1

    except (
        TypeError,
        ValueError,
        RuntimeError,
        KeyError,
        AssertionError,
    ) as error:
        print()
        print(
            f"ERROR: {error}"
        )

        return 1

    except KeyboardInterrupt:
        print()
        print(
            "Proceso cancelado por el usuario."
        )

        return 130


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
