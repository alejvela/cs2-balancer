from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from application.balance_validation import get_player_identity
from application.global_execution import get_player_attribute, get_player_nickname
from application.results.base_report_result import BaseReportResult
from application.results.global_report_result import GlobalReportResult
from application.results.report_mode import ReportMode
from configuration.application_config import ApplicationConfig
from optimizer.modes.optimization_mode import OptimizationMode
from scoring.scoring_model import ScoringModel


def print_global_optimization(
    result: GlobalReportResult,
) -> None:
    print()
    print("=" * 72)
    print("OPTIMIZACIÓN GLOBAL")
    print("=" * 72)

    initial = result.initial_incumbent_score
    print("Incumbent inicial:      " + (
        "No disponible (sin solución inicial)" if initial is None else f"{initial:.4f}"
    ))

    print(f"Score final:            {result.score:.4f}")

    improvement = result.improvement
    print("Mejora GLOBAL:          " + (
        "No disponible (sin solución inicial)"
        if improvement is None else f"{improvement:+.4f}"
    ))

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
        initial = result.initial_score
        print("Puntuación inicial:   " + (
            "No disponible (sin solución inicial)" if initial is None else f"{initial:.2f}"
        ))

        print(f"Puntuación final:     {result.final_score:.2f}")

        improvement = result.improvement
        print("Mejora total:         " + (
            "No disponible (sin solución inicial)"
            if improvement is None else f"{improvement:+.2f}"
        ))

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


def print_report_path(exported_path: Path) -> None:
    print()
    print(f"Informe HTML generado en: {exported_path.resolve()}")
