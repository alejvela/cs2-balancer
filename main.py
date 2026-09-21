from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from application.balancing_application import BalancingApplication
from application.balancing_request import BalancingRequest
from application.global_execution import get_player_attribute, get_player_nickname
from application.results.base_report_result import BaseReportResult
from application.results.global_report_result import GlobalReportResult
from application.results.report_mode import ReportMode
from configuration.application_config import ApplicationConfig
from configuration.reporting_factory import create_reporting_components
from importers.csstats_importer import CssStatsImporter
from optimizer.modes.optimization_mode import OptimizationMode
from scoring.scoring_model import ScoringModel
from scrapers.csv_escraper_exporter import CsvScraperExporter
from scrapers.faceit.faceit_api_client import FaceitApiClient
from scrapers.faceit.faceit_player_record_map import FaceitPlayerRecordMapper
from scrapers.faceit.faceit_scrapper import FaceitScraper


def print_global_optimization(
    result: GlobalReportResult,
) -> None:
    print()
    print("=" * 72)
    print("OPTIMIZACIÓN GLOBAL")
    print("=" * 72)

    print(f"Incumbent inicial:      {result.initial_incumbent_score:.4f}")

    print(f"Score final:            {result.score:.4f}")

    print(f"Mejora GLOBAL:          {result.improvement:+.4f}")

    print(f"Nodos explorados:       {result.nodes_visited:,}")

    print(f"Soluciones evaluadas:   {result.complete_solutions_evaluated:,}")

    print(f"Ramas podadas:          {result.pruned_nodes:,}")

    print(f"  Capacidad:            {result.capacity_prunes:,}")

    print(f"  Seeds:                {result.seed_prunes:,}")

    print(f"  Bound / Power:        {result.bound_prunes:,}")

    print(f"Tiempo GLOBAL:          {format_elapsed_seconds(result.elapsed_seconds)}")

    print(f"Límite alcanzado:       {'SÍ' if result.stopped_by_limit else 'NO'}")

    print(
        f"Espacio agotado:        "
        f"{'SÍ' if result.stop_reason == 'SEARCH_EXHAUSTED' else 'NO'}"
    )

    print(f"Óptimo demostrado:      {'SÍ' if result.optimality_proven else 'NO'}")

    print(f"Motivo de parada:       {result.stop_reason}")


def get_faceit_api_key() -> str:
    """
    Obtiene la API key de FACEIT desde la variable de entorno
    FACEIT_API_KEY.
    """

    api_key = os.environ.get("FACEIT_API_KEY")

    if api_key is None:
        raise RuntimeError("La variable de entorno FACEIT_API_KEY no está definida.")

    normalized = api_key.strip()

    if not normalized:
        raise RuntimeError("La variable de entorno FACEIT_API_KEY está vacía.")

    return normalized


def run_faceit_import(config: ApplicationConfig) -> Path:
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

    if not config.paths.source_players.exists():
        raise FileNotFoundError(
            f"No existe el archivo de entrada: {config.paths.source_players.resolve()}"
        )

    api_key = get_faceit_api_key()

    print()
    print("=" * 72)
    print("IMPORTACIÓN DE JUGADORES DESDE FACEIT")
    print("=" * 72)

    print(f"Entrada:              {config.paths.source_players}")

    print(f"Juego preferido:      {config.faceit.preferred_game_id}")

    print(f"Juegos fallback:      {', '.join(config.faceit.fallback_game_ids)}")

    print(f"Partidas recientes:   {config.faceit.recent_matches}")

    print()

    with FaceitApiClient(
        api_key=api_key,
        preferred_game_id=(config.faceit.preferred_game_id),
        fallback_game_ids=(config.faceit.fallback_game_ids),
        timeout=config.faceit.timeout_seconds,
        retries=config.faceit.retries,
        retry_delay=(config.faceit.retry_delay_seconds),
    ) as client:
        mapper = FaceitPlayerRecordMapper(
            game_id=config.faceit.preferred_game_id,
            source_name="FACEIT",
        )

        scraper = FaceitScraper(
            client=client,
            mapper=mapper,
            recent_matches=config.faceit.recent_matches,
            strict=config.faceit.strict,
            delay=config.faceit.delay_seconds,
            maximum_seed_one_players=(config.event.number_of_teams),
        )

        records = scraper.scrape(config.paths.source_players)

        scraper_errors = scraper.errors

    valid_records = [record for record in records if record.is_valid]

    failed_records = [record for record in records if not record.is_valid]

    print(f"Jugadores esperados:  {config.event.expected_player_count}")

    print(f"Jugadores válidos:    {len(valid_records)}")

    print(f"Jugadores con error:  {len(failed_records)}")

    if failed_records:
        print()
        print("JUGADORES CON ERROR")
        print("-" * 72)

        for record in failed_records:
            print(f"- {record.nickname}: {record.error or 'Error desconocido'}")

        CsvScraperExporter(
            include_errors=True,
        ).export(
            records=failed_records,
            output=config.paths.faceit_errors,
        )

        print()

        print(f"Errores guardados en: {config.paths.faceit_errors.resolve()}")

    if scraper_errors:
        print()
        print("DETALLE TÉCNICO")
        print("-" * 72)

        for error in scraper_errors:
            print(
                f"Fila {error.get('row')}: "
                f"{error.get('nick')} / "
                f"{error.get('faceit_nickname')} -> "
                f"{error.get('error')}"
            )

    if len(valid_records) != config.event.expected_player_count:
        raise RuntimeError(
            "El número de jugadores válidos no coincide "
            "con el esperado. "
            f"Esperados: {config.event.expected_player_count}. "
            f"Obtenidos: {len(valid_records)}."
        )

    generated_file = CsvScraperExporter(
        include_errors=False,
    ).export(
        records=valid_records,
        output=config.paths.generated_stats,
    )

    print()

    print(f"CSV de estadísticas generado: {generated_file.resolve()}")

    return generated_file


def resolve_players_file(config: ApplicationConfig) -> Path:
    """
    Devuelve el CSV que debe utilizar la aplicación.

    Cuando config.faceit.run_import=True se regeneran primero las
    estadísticas.

    Cuando es False se reutiliza players_stats.csv.
    """

    if config.faceit.run_import:
        return run_faceit_import(config)

    if not config.paths.generated_stats.exists():
        raise FileNotFoundError(
            f"No existe el archivo generado: {config.paths.generated_stats.resolve()}"
        )

    return config.paths.generated_stats


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
        return str(identity).strip().casefold()

    steam_id = get_player_attribute(
        player,
        "steam_id",
    )

    if steam_id:
        return f"steam:{str(steam_id).strip().casefold()}"

    nickname = get_player_nickname(player)

    return f"nick:{nickname.strip().casefold()}"


def validate_players(
    players: Iterable[Any],
    expected_player_count: int,
) -> None:
    """
    Verifica la colección de jugadores antes de ejecutar el
    balanceador.
    """

    player_list = list(players)

    if len(player_list) != expected_player_count:
        raise RuntimeError(
            f"Se han importado {len(player_list)} jugadores. "
            f"Se esperaban {expected_player_count}."
        )

    object_ids = [id(player) for player in player_list]

    if len(object_ids) != len(set(object_ids)):
        raise RuntimeError(
            "La colección de entrada contiene instancias de Player duplicadas."
        )

    identities = [get_player_identity(player) for player in player_list]

    duplicated = [
        identity for identity, count in Counter(identities).items() if count > 1
    ]

    if duplicated:
        raise RuntimeError(
            f"La colección de entrada contiene jugadores duplicados: {duplicated}."
        )


def validate_teams(
    teams: Iterable[Any],
    expected_team_size: int,
    expected_player_count: int,
    stage: str,
    config: ApplicationConfig,
) -> None:
    """
    Comprueba:

        - Número de equipos.
        - Tamaño de cada equipo.
        - Número total de jugadores.
        - Instancias duplicadas.
        - Identidades duplicadas.
    """

    team_list = list(teams)

    if len(team_list) != config.event.number_of_teams:
        raise RuntimeError(
            f"[{stage}] Se esperaban "
            f"{config.event.number_of_teams} equipos, "
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

        if len(players) != expected_team_size:
            raise RuntimeError(
                f"[{stage}] {team_name} contiene "
                f"{len(players)} jugadores. "
                f"Se esperaban {expected_team_size}."
            )

        total_players += len(players)

        for player_index, player in enumerate(
            players,
            start=1,
        ):
            location = f"{team_name}[{player_index}]"

            object_locations.setdefault(
                id(player),
                [],
            ).append(location)

            identity_locations.setdefault(
                get_player_identity(player),
                [],
            ).append(location)

    if total_players != expected_player_count:
        raise RuntimeError(
            f"[{stage}] Existen "
            f"{total_players} posiciones de jugadores. "
            f"Se esperaban {expected_player_count}."
        )

    duplicated_objects = {
        object_id: locations
        for object_id, locations in object_locations.items()
        if len(locations) > 1
    }

    duplicated_identities = {
        identity: locations
        for identity, locations in identity_locations.items()
        if len(locations) > 1
    }

    if duplicated_objects:
        details = "; ".join(
            (f"object_id={object_id}: {', '.join(locations)}")
            for object_id, locations in duplicated_objects.items()
        )

        raise RuntimeError(
            f"[{stage}] Se han detectado instancias de Player repetidas. {details}"
        )

    if duplicated_identities:
        details = "; ".join(
            (f"{identity}: {', '.join(locations)}")
            for identity, locations in duplicated_identities.items()
        )

        raise RuntimeError(
            f"[{stage}] Se han detectado jugadores duplicados por identidad. {details}"
        )


def validate_same_player_collection(
    players_before: Iterable[Any],
    teams_after: Iterable[Any],
) -> None:
    """
    Garantiza que el proceso conserva exactamente la misma
    colección lógica de jugadores.
    """

    before_counter = Counter(get_player_identity(player) for player in players_before)

    after_counter = Counter(
        get_player_identity(player) for team in teams_after for player in team.players
    )

    if before_counter == after_counter:
        return

    missing = before_counter - after_counter

    unexpected = after_counter - before_counter

    raise RuntimeError(
        "El proceso ha modificado la colección de jugadores. "
        f"Ausentes: {dict(missing)}. "
        f"Inesperados: {dict(unexpected)}."
    )


def validate_result(
    result: BaseReportResult,
    players: Iterable[Any],
    config: ApplicationConfig,
) -> None:
    """
    Ejecuta las validaciones comunes y específicas del modo.
    """

    if not isinstance(
        result,
        BaseReportResult,
    ):
        raise TypeError("result must be a BaseReportResult instance.")

    validate_teams(
        teams=result.teams,
        expected_team_size=config.event.team_size,
        expected_player_count=(config.event.expected_player_count),
        stage="Resultado",
        config=config,
    )

    validate_same_player_collection(
        players_before=players,
        teams_after=result.teams,
    )

    if result.mode is ReportMode.OPTIMIZED:
        if result.final_score < result.initial_score:
            raise RuntimeError(
                "La optimización ha terminado con una "
                "puntuación inferior a la inicial. "
                f"Inicial: {result.initial_score:.2f}. "
                f"Final: {result.final_score:.2f}."
            )

    elif result.mode is ReportMode.PREASSIGNED:
        validate_preassigned_result(result)


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
                errors.append(f"{get_player_nickname(player)} no contiene Team.")

                continue

            try:
                assigned_team_value = int(assigned_team)

            except (
                TypeError,
                ValueError,
            ):
                errors.append(
                    f"{get_player_nickname(player)} contiene Team={assigned_team!r}."
                )

                continue

            try:
                actual_team_value = int(team_id)

            except (
                TypeError,
                ValueError,
            ):
                actual_team_value = team_index

            if assigned_team_value != actual_team_value:
                errors.append(
                    f"{get_player_nickname(player)} "
                    f"tiene Team={assigned_team_value}, "
                    f"pero aparece en "
                    f"Equipo {actual_team_value}."
                )

    if errors:
        raise RuntimeError(
            "La evaluación preasignada no ha conservado "
            "correctamente los equipos: " + " | ".join(errors)
        )


def print_mode(
    mode: ReportMode,
    config: ApplicationConfig,
) -> None:
    """
    Muestra por consola qué flujo va a ejecutarse.
    """

    print()
    print("=" * 72)
    print("MODO DE EJECUCIÓN")
    print("=" * 72)

    print(f"Modo:                 {mode.value}")

    print(f"Descripción:          {mode.label}")

    if mode is ReportMode.PREASSIGNED:
        print("Acción:               Evaluar equipos del CSV")

        print("Optimización:         NO")

    else:
        print("Acción:               Generar y optimizar equipos")

        print("Optimización:         SÍ")

        print(f"Motor:                {config.optimization_mode.value.upper()}")


def print_players_debug(
    players: Iterable[Any],
) -> None:
    """
    Muestra los datos básicos importados.
    """

    print()
    print("=" * 72)
    print("JUGADORES IMPORTADOS")
    print("=" * 72)

    for index, player in enumerate(
        players,
        start=1,
    ):
        nickname = get_player_nickname(player)

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


def print_team_debug(
    teams: Iterable[Any],
    title: str,
) -> None:
    """
    Muestra la composición de los equipos.
    """

    print()
    print("=" * 72)
    print(title)
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
        print(str(team_name).upper())
        print("-" * 72)

        for player_index, player in enumerate(
            team.players,
            start=1,
        ):
            nickname = get_player_nickname(player)

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


def format_confidence(
    value: Any,
) -> str:
    normalized = str(value or "UNKNOWN").strip().upper()

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

    normalized = str(value).strip().casefold()

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
        return str(int(value))
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
        return f"{seconds * 1000.0:.2f} ms"

    if seconds < 60.0:
        return f"{seconds:.2f} s"

    minutes = int(seconds // 60.0)

    remaining_seconds = seconds - minutes * 60.0

    return f"{minutes} min {remaining_seconds:.1f} s"


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

    stable_data = metadata.get("stable_optimization")

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

    score = stable_data.get("score")

    if score is not None:
        print(f"Score seleccionado:    {float(score):.4f}")

    penalty = stable_data.get("penalty")

    if penalty is not None:
        print(f"Penalización:          {float(penalty):.2f}")

    print(f"Confianza:             {format_confidence(stable_data.get('confidence'))}")

    print(f"Restarts completados:  {stable_data.get('completed_restarts', 0)}")

    print(f"Soluciones únicas:     {stable_data.get('unique_solutions', 0)}")

    print(
        f"Mejor encontrada en:   "
        f"{format_restart_number(stable_data.get('best_restart_number'))}"
    )

    print(
        f"Sin mejora:            {convergence.get('restarts_without_improvement', 0)}"
    )

    print(f"Mejoras reales:        {stable_data.get('quality_improvements', 0)}")

    print(f"Cambios selección:     {stable_data.get('selection_changes', 0)}")

    print(f"Evaluaciones globales: {convergence.get('total_evaluations', 0)}")

    print(
        f"Target alcanzado:      "
        f"{'SÍ' if stable_data.get('target_reached', False) else 'NO'}"
    )

    print(
        f"Target confirmado:     "
        f"{'SÍ' if stable_data.get('target_confirmed', False) else 'NO'}"
    )

    print(
        f"Motivo de parada:      {format_stop_reason(stable_data.get('stop_reason'))}"
    )

    print(
        f"Tiempo total STABLE:   "
        f"{format_elapsed_seconds(stable_data.get('elapsed_seconds', 0.0))}"
    )

    signature_hash = signature.get("hash")

    if signature_hash:
        print(f"Firma solución:        {signature_hash}")


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
        print("No hay restricciones disponibles.")
        return

    if isinstance(
        restrictions,
        dict,
    ):
        items = tuple(restrictions.items())
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

        weighted_score = score * weight

        contribution = weighted_score / 100.0

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

    weighted_average = total_weighted / total_weight if total_weight > 0.0 else 0.0

    print(f"{'MEDIA PONDERADA':<24}| {weighted_average:7.2f}")

    print(f"{'PENALIZACIÓN TOTAL':<24}| {total_penalty:7.2f}")

    print(f"{'SCORE FINAL':<24}| {result.final_score:7.2f}")


def print_result(
    result: BaseReportResult,
    scoring_model: ScoringModel,
) -> None:
    """
    Muestra un resumen completo compatible con ambos modos.
    """

    print()
    print("=" * 72)
    print("LAN CS2 TEAM BALANCER")
    print("=" * 72)

    print(f"Modo:                 {result.mode.label}")

    if result.optimized:
        print(f"Puntuación inicial:   {result.initial_score:.2f}")

        print(f"Puntuación final:     {result.final_score:.2f}")

        print(f"Mejora total:         {result.improvement:+.2f}")

        print(f"Movimientos:          {result.iterations}")

        print(f"Evaluaciones:         {result.total_evaluations}")

        print(f"Tiempo optimización:  {result.elapsed_ms:.2f} ms")

        optimization_mode = getattr(
            result,
            "metadata",
            {},
        ).get("optimization_mode")

        print(f"Motor optimización:   {str(optimization_mode or 'fast').upper()}")

    else:
        print(f"Puntuación equilibrio: {result.final_score:.2f}")

        print(f"Clasificación:        {result.balance_label}")

        print(f"Evaluaciones:         {result.total_evaluations}")

        print(f"Tiempo evaluación:    {result.elapsed_ms:.2f} ms")

    print(f"Penalización:         {result.penalty:.2f}")

    print(f"Composición válida:   {'SÍ' if result.is_valid else 'NO'}")

    print(f"Equipos:              {result.team_count}")

    print(f"Jugadores:            {result.player_count}")

    if (
        result.optimized
        and getattr(
            result,
            "metadata",
            {},
        ).get("optimization_mode")
        == OptimizationMode.STABLE.value
    ):
        print_stable_optimization(result)

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
        print(str(team_name).upper())
        print("-" * 72)

        team_powers: list[float] = []

        for player in team.players:
            nickname = get_player_nickname(player)

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

            power = scoring_model.power(player)

            team_powers.append(power)

            elo_text = str(int(float(elo))) if elo is not None else "N/A"

            level_text = str(int(float(level))) if level is not None else "N/A"

            kd_text = f"{float(kd):.2f}" if kd is not None else "N/A"

            adr_text = f"{float(adr):.1f}" if adr is not None else "N/A"

            team_text = str(team_number) if team_number is not None else "—"

            print(
                f"  {nickname:<20}"
                f"| Power: {power:6.2f} "
                f"| ELO: {elo_text:<5} "
                f"| LVL: {level_text:<3} "
                f"| KD: {kd_text:<5} "
                f"| ADR: {adr_text:<5} "
                f"| Team: {team_text}"
            )

        average_power = sum(team_powers) / len(team_powers) if team_powers else 0.0

        print(f"  {'':20}| Power medio: {average_power:.2f}")

    print()


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


def main() -> int:
    """Supported developer bootstrap: I/O, one application call, presentation."""
    try:
        config = ApplicationConfig.production_defaults()
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
        print()
        print(f"Informe HTML generado en: {exported_path.resolve()}")
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
