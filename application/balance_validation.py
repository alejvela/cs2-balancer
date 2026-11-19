from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from application.global_execution import get_player_attribute, get_player_nickname
from application.results.base_report_result import BaseReportResult
from application.results.report_mode import ReportMode
from configuration.application_config import ApplicationConfig


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
        if result.initial_score is not None and result.final_score < result.initial_score:
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
