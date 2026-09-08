"""Render prepared tournament reports only; no imports, scoring or award rules."""

import re
from dataclasses import fields
from html import escape
from pathlib import Path

from exporters.tournament_styles import TOURNAMENT_CSS
from models.player_merit import PlayerMerit
from models.tournament_report import (
    LeaderboardReport,
    PlayerReport,
    SeriesReport,
    TournamentReport,
)

# Presentation labels only: domain identifiers and CSV columns remain unchanged.
STAT_LABELS = {
    "kills": "Bajas",
    "deaths": "Muertes",
    "damage": "Daño",
    "assists": "Asistencias",
    "enemy5ks": "Multikills de 5 bajas",
    "enemy4ks": "Multikills de 4 bajas",
    "enemy3ks": "Multikills de 3 bajas",
    "enemy2ks": "Multikills de 2 bajas",
    "utility_count": "Usos de utilidad",
    "utility_damage": "Daño de utilidad",
    "utility_successes": "Usos de utilidad efectivos",
    "utility_enemies": "Enemigos afectados por utilidad",
    "flash_count": "Flashes lanzadas",
    "flash_successes": "Flashes efectivas",
    "health_points_removed_total": "Puntos de vida eliminados",
    "health_points_dealt_total": "Puntos de vida infligidos",
    "shots_fired_total": "Disparos realizados",
    "shots_on_target_total": "Disparos al objetivo",
    "v1_count": "Intentos de clutch 1v1",
    "v1_wins": "Victorias de clutch 1v1",
    "v2_count": "Intentos de clutch 1v2",
    "v2_wins": "Victorias de clutch 1v2",
    "entry_count": "Intentos de apertura",
    "entry_wins": "Aperturas ganadas",
    "equipment_value": "Valor del equipamiento",
    "money_saved": "Dinero ahorrado",
    "kill_reward": "Recompensa por bajas",
    "live_time": "Tiempo con vida",
    "head_shot_kills": "Bajas de headshot",
    "cash_earned": "Dinero obtenido",
    "enemies_flashed": "Enemigos cegados",
    "maps_played": "Mapas jugados",
    "required_maps": "Mapas requeridos",
    "maximum_maps_played": "Máximo de mapas jugados",
    "damage_per_map": "Daño / mapa",
    "damage_score": "Puntuación de daño",
    "kills_per_map": "Bajas / mapa",
    "kill_score": "Puntuación de bajas",
    "survival_engagement_score": "Puntuación de supervivencia en enfrentamientos",
    "headshot_rate_unweighted": "Proporción de headshots (sin ponderar)",
    "accuracy_unweighted": "Precisión (sin ponderar)",
    "entry_attempts": "Intentos de apertura",
    "entry_wins_per_map": "Aperturas ganadas / mapa",
    "entry_success_rate": "Conversión de aperturas",
    "opportunity_confidence": "Confianza por oportunidades",
    "weighted_multikill_value": "Valor ponderado de multikills",
    "weighted_multikill_value_per_map": "Valor ponderado de multikills / mapa",
    "v1_attempts": "Intentos de clutch 1v1",
    "v2_attempts": "Intentos de clutch 1v2",
    "weighted_supported_clutch_wins": "Victorias de clutch ponderadas",
    "supported_clutch_success_rate": "Conversión de clutch",
    "assists_per_map": "Asistencias / mapa",
    "utility_damage_per_map": "Daño de utilidad / mapa",
    "utility_success_rate": "Efectividad de la utilidad",
    "utility_opportunity_confidence": "Confianza por oportunidades de utilidad",
    "utility_bucket_score": "Puntuación de utilidad",
    "enemies_flashed_per_map": "Enemigos cegados / mapa",
    "flash_success_rate": "Efectividad de las flashes",
    "flash_opportunity_confidence": "Confianza por oportunidades de flash",
    "flash_bucket_score": "Puntuación de flash",
    "K/D": "K/D",
    "Kills / map": "Bajas / mapa",
    "Damage / map": "Daño / mapa",
    "Assists / map": "Asistencias / mapa",
    "Headshot rate": "% Headshots",
    "Accuracy": "Precisión",
    "Entry conversion": "Conversión de aperturas",
    "Supported clutch conversion": "Conversión de clutch",
    "Flash conversion": "Efectividad de las flashes",
    "Utility conversion": "Efectividad de la utilidad",
    "maximum": "Máximo",
    "minimum": "Mínimo",
}

COMPONENT_LABELS = {
    "combat": "Combate",
    "opening": "Aperturas / Entry",
    "multikill": "Multikill",
    "supported_clutch": "Clutch",
    "teamplay": "Juego en equipo",
    "utility_flash": "Utilidad / Flash",
}

CATEGORY_LABELS = {
    "combat": "Combate",
    "opening": "Aperturas",
    "clutch": "Clutch",
    "multikill": "Multikill",
    "support": "Apoyo",
    "utility": "Utilidad",
    "precision": "Precisión",
    "survival": "Supervivencia",
    "economy": "Economía",
}


def _formula_label(value: str) -> str:
    """Localize formula display tokens without evaluating or altering the formula."""
    return re.sub(
        r"[A-Za-z_][A-Za-z_0-9]*",
        lambda match: STAT_LABELS.get(match[0], match[0]),
        value,
    )


def _eligibility_reason(player: PlayerReport) -> str:
    eligibility = player.entry.tournament_eligibility
    if eligibility is None:
        return "No se aplica en este ámbito."
    return f"Mapas jugados: {eligibility.maps_played}. Mínimo requerido: {eligibility.required_maps}."


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _number(value: int | float) -> str:
    return _text(str(value) if isinstance(value, int) else f"{value:.2f}")


def _anchor(player_id: str) -> str:
    return "player-" + player_id.encode("utf-8").hex()


def _pairs(pairs) -> str:
    return (
        "<dl>"
        + "".join(
            f"<dt>{_text(label)}</dt><dd>{_text(value)}</dd>" for label, value in pairs
        )
        + "</dl>"
    )


def _eligibility(player: PlayerReport) -> str:
    eligibility = player.entry.tournament_eligibility
    if eligibility is None:
        return "—"
    label = (
        "Elegible para MVP" if eligibility.eligible else "No elegible para MVP global"
    )
    return f'<span class="badge" title="{_text(_eligibility_reason(player))}">{label}</span>'


def _leaderboard(board: LeaderboardReport, caption: str) -> str:
    rows = []
    for player in board.players:
        entry, stats = player.entry, player.entry.statistics
        metrics = {metric.label: metric.value for metric in player.metrics}
        name = f'<a href="#{_anchor(entry.player_id)}">{_text(entry.display_name)}</a>'
        cells = (
            _text(entry.rank),
            name,
            _number(entry.impact.score),
            _text(entry.maps_played),
            _text(stats.raw.kills),
            _text(stats.raw.deaths),
            _text(metrics["K/D"]),
            _text(metrics["Damage / map"]),
            _text(stats.raw.assists),
            _text(stats.raw.entry_wins),
            _text(stats.supported_clutch_wins),
            _text(metrics["Headshot rate"]),
            _eligibility(player),
        )
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    headers = (
        "Posición",
        "Jugador",
        "Impact",
        "Mapas",
        "Bajas",
        "Muertes",
        "K/D",
        "Daño / mapa",
        "Asistencias",
        "Aperturas ganadas",
        "Victorias 1v1 + 1v2",
        "% Headshots",
        "Elegibilidad",
    )
    return (
        '<div class="table-wrap"><table><caption>'
        + _text(caption)
        + "</caption><thead><tr>"
        + "".join(f'<th scope="col">{_text(label)}</th>' for label in headers)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        + (
            '<p class="muted">No hay jugadores con datos validados.</p>'
            if not rows
            else ""
        )
    )


def _award(merit: PlayerMerit) -> str:
    evidence = _pairs((STAT_LABELS[item.metric], item.value) for item in merit.evidence)
    return f'''<article class="card award" data-rule="{_text(merit.rule_id)}">
<p class="eyebrow">{_text(CATEGORY_LABELS[merit.category.value])}</p><h3>{_text(merit.title)}</h3>
<p class="recipient"><a href="#{_anchor(merit.player_id)}">{_text(merit.display_name)}</a></p>
<p class="value">{_number(merit.evidence_value)}</p><p>{_text(_formula_label(merit.evidence_label))}</p>
<p class="muted">{_text(_formula_label(merit.explanation))}</p><details><summary>Evidencia numérica</summary>{evidence}</details></article>'''


def _player_detail(player: PlayerReport) -> str:
    entry = player.entry
    components = []
    for component in entry.impact.components:
        evidence = _pairs(
            (STAT_LABELS[item.metric], _number(item.value))
            for item in component.evidence
        )
        components.append(f'''<div class="component"><h4>{_text(COMPONENT_LABELS[component.component_id])}</h4>
<p>{_number(component.score)} / 100 · peso {_text(f"{component.weight:.0%}")}</p>
<meter min="0" max="100" value="{_text(component.score)}" aria-label="{_text(COMPONENT_LABELS[component.component_id])}">{_number(component.score)}</meter>
<p>Contribución: {_number(component.weighted_contribution)}</p>
<details><summary>Evidencia del componente</summary>{evidence}</details></div>''')
    raw = entry.statistics.raw
    totals = _pairs(
        (STAT_LABELS[field.name], getattr(raw, field.name)) for field in fields(raw)
    )
    derived = _pairs(
        (STAT_LABELS[metric.label], metric.value) for metric in player.metrics
    )
    awards = "".join(
        f"<li>{_text(merit.title)} · {_number(merit.evidence_value)}</li>"
        for merit in player.merits
    )
    return f'''<details id="{_anchor(entry.player_id)}" class="player-detail" open>
<summary>#{entry.rank} · {_text(entry.display_name)} · Impact {_number(entry.impact.score)}</summary>
<p class="provenance">steamid64: {_text(entry.player_id)} · {entry.maps_played} mapas · {entry.series_played} series</p>
<p>Alias: {_text(", ".join(entry.observed_aliases))}<br>Equipos: {_text(", ".join(entry.observed_teams))}</p>
<p>{_eligibility(player)}</p><div class="grid"><div><h4>Totales</h4>{totals}</div>
<div><h4>Estadísticas derivadas</h4>{derived}<p class="muted">— indica un valor no disponible. K/D conserva la convención existente: se usa un mínimo de 1 muerte como divisor. La unidad del tiempo con vida no está especificada; los valores económicos son estadísticas brutas.</p>
<h4>Premios y títulos</h4><ul>{awards or "<li>Sin títulos obtenidos.</li>"}</ul></div></div>
<h4>Desglose de impacto · Impact {_number(entry.impact.score)} · v{_text(entry.impact.model_version)}</h4>
<div class="components">{"".join(components)}</div></details>'''


def _series(series: SeriesReport) -> str:
    best_of = (
        series.best_of.name
        if series.best_of is not None
        else "Formato BO no disponible"
    )
    status = (
        "Serie aceptada"
        if series.accepted
        else "Metadatos de serie pendientes o no válidos"
    )
    maps = []
    for played_map in series.maps:
        maps.append(f"""<details open><summary>Mapa {_text(played_map.mapnumber)} · matchid {_text(played_map.matchid)}</summary>
<p class="provenance">CSV de origen: {_text(played_map.source)}</p>
{_leaderboard(played_map.leaderboard, "Clasificación del mapa")}</details>""")
    return f"""<article class="card series"><h3>{_text(series.display_name)}</h3>
<p class="badge">{_text(best_of)} · {len(series.maps)} mapas jugados · {status}</p>
<p class="provenance">Identificador de la carpeta de serie: {_text(series.series_id)}</p>
<p class="muted">El número de mapas no permite confirmar si la serie ha terminado; el origen no incluye su resultado.</p>
<h4>Resultado agregado de la serie</h4>{_leaderboard(series.leaderboard, "Clasificación de la serie a partir de sus estadísticas agregadas")}
<h4>Resultados por mapa</h4>{"".join(maps)}</article>"""


def _diagnostics(report: TournamentReport) -> str:
    imported = report.import_result

    def issue_key(item):
        return (str(item.path).casefold(), str(item.path), item.message)

    invalid = "".join(
        f"<li><strong>{_text(item.path)}</strong>: {_text(item.message)}</li>"
        for item in sorted(imported.invalid_files, key=issue_key)
    )
    issues = "".join(
        f"<li><strong>{_text(item.path)}</strong>: {_text(item.message)}</li>"
        for item in sorted(imported.series_issues, key=issue_key)
    )
    duplicates = "".join(
        f"<li>{_text(item.path)} → original: {_text(item.original_path)}; huella digital {_text(item.fingerprint)}</li>"
        for item in sorted(imported.skipped_duplicates, key=lambda item: str(item.path))
    )
    empty = "".join(
        f"<li>{_text(folder)}: sin mapas aceptados (carpeta vacía, con datos rechazados o solo duplicados).</li>"
        for folder in report.empty_folders
    )
    pending = "".join(
        _series(series) for series in report.series if not series.accepted
    )
    provenance = "".join(
        f"<li>{_text(item.path)} · huella digital {_text(item.fingerprint)}</li>"
        for item in sorted(imported.imported_files, key=lambda item: str(item.path))
    )
    return f"""<section id="quality"><p class="eyebrow">Transparencia de la importación</p><h2>Calidad de los datos</h2>
<p class="muted">Los mensajes técnicos originales se conservan para identificar el problema en los datos de origen.</p>
<p class="provenance">Origen del torneo: {_text(imported.root)}</p>
<div class="grid"><div class="card"><h3>CSV no válidos · {len(imported.invalid_files)}</h3><ul>{invalid or "<li>Ninguno.</li>"}</ul></div>
<div class="card"><h3>Incidencias de las series · {len(imported.series_issues)}</h3><ul>{issues or "<li>Ninguno.</li>"}</ul></div>
<div class="card"><h3>Duplicados omitidos · {len(imported.skipped_duplicates)}</h3><ul>{duplicates or "<li>Ninguno.</li>"}</ul></div></div>
<h3>Carpetas sin mapas aceptados</h3><ul>{empty or "<li>Ninguno.</li>"}</ul>
<h3>Series pendientes de metadatos válidos</h3>
<p class="muted">Estos mapas validados y sin duplicados se incluyen en las estadísticas generales según el contrato de agregación existente. Los CSV rechazados nunca contribuyen.</p>
{pending or "<p>Ninguno.</p>"}<details><summary>Procedencia de los CSV aceptados</summary><ul>{provenance or "<li>Ninguno.</li>"}</ul></details></section>"""


class TournamentHtmlExporter:
    """Render and write a prepared report without invoking any domain service."""

    def render(self, report: TournamentReport) -> str:
        imported = report.import_result
        overview = (
            (len(imported.series), "Series aceptadas"),
            (report.statistics.map_count, "Mapas validados"),
            (len(report.leaderboard.players), "Jugadores del torneo"),
            (len(imported.imported_files), "CSV importados"),
        )
        cards = "".join(
            f'<div class="card stat"><strong>{count}</strong><span>{_text(label)}</span></div>'
            for count, label in overview
        )
        mvp = report.mvp
        if mvp is None:
            mvp_html = (
                "<p>MVP no disponible: ningún jugador clasificado es elegible.</p>"
            )
        else:
            entry = mvp.entry
            mvp_html = f"""<div class="card mvp"><div><p class="eyebrow">MVP del torneo</p>
<h3><a href="#{_anchor(entry.player_id)}">{_text(entry.display_name)}</a></h3><p class="score">{_number(entry.impact.score)}</p>
<p>Impact · v{_text(entry.impact.model_version)}</p></div><div><h3>Primer jugador elegible de la clasificación general</h3>
<p>Posición #{entry.rank} · {entry.maps_played} mapas · {entry.statistics.raw.kills} bajas · {_number(entry.statistics.damage_per_map)} daño / mapa</p>
<p>{_text(_eligibility_reason(mvp))}</p><p class="muted">Reconocimiento competitivo basado en la clasificación existente. Los títulos siguientes son distinciones estadísticas independientes.</p></div></div>"""
        series_html = "".join(
            _series(series) for series in report.series if series.accepted
        )
        merits_html = "".join(_award(merit) for merit in report.merits.merits)
        return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_text(report.title)}</title><style>{TOURNAMENT_CSS}</style></head>
<body><main><header class="hero"><p class="eyebrow">Counter-Strike 2 / Estadísticas de la LAN</p><h1>{_text(report.title)}</h1>
<p class="muted">Cada mapa y cada contribución, en un único informe del torneo.</p></header>
<nav aria-label="Secciones del informe"><a href="#overview">Resumen</a><a href="#leaderboard">Clasificación</a><a href="#merits">Premios y títulos</a><a href="#series">Series y mapas</a><a href="#players">Jugadores</a><a href="#quality">Calidad de los datos</a></nav>
<section id="overview"><h2>Resumen del torneo</h2><div class="grid">{cards}</div>
<p>{imported.discovered_csv_count} CSV encontrados · {len(imported.skipped_duplicates)} duplicados omitidos · {len(imported.invalid_files)} CSV no válidos · {len(imported.series_issues)} incidencias de las series. <a href="#quality">Ver incidencias de importación</a></p>
<p class="muted">Los resultados generales incluyen todos los mapas validados y sin duplicados, también los de carpetas pendientes de un formato BO válido. Las series aceptadas se cuentan por separado.</p>{mvp_html}</section>
<section id="leaderboard"><p class="eyebrow">Rendimiento competitivo</p><h2>Clasificación general</h2>
<p class="muted">Impact v{_text(report.leaderboard.ranking.model_version)}. Todos los jugadores mantienen su posición; la elegibilidad para MVP se muestra por separado.</p>
{_leaderboard(report.leaderboard, "Clasificación del torneo — orden canónico")}</section>
<section id="merits"><p class="eyebrow">Los protagonistas de la LAN</p><h2>Premios y títulos</h2><p class="muted">Un ganador por título. Un jugador puede obtener varios títulos.</p>
<div class="grid">{merits_html or "<p>No hay títulos disponibles.</p>"}</div>
<p class="muted">Charmander no está disponible: no hay un dato específico de daño de molotov, incendiaria o fuego. El Alquimista utiliza únicamente daño de utilidad genérico.</p></section>
<section id="series"><p class="eyebrow">Archivo de partidas</p><h2>Series aceptadas y mapas</h2>{series_html or "<p>No hay series aceptadas. Consulta los mapas conservados en Calidad de los datos.</p>"}</section>
<section id="players"><p class="eyebrow">Más allá de la clasificación</p><h2>Estadísticas por jugador</h2>{"".join(_player_detail(player) for player in report.leaderboard.players) or "<p>No hay jugadores con datos validados.</p>"}</section>
{_diagnostics(report)}<footer>Informe autónomo de la LAN · Impact v{_text(report.leaderboard.ranking.model_version)} · Sin dependencias externas</footer>
</main></body></html>"""

    def export(self, report: TournamentReport, output: str | Path) -> Path:
        path = Path(output)
        if path.suffix.lower() != ".html":
            path = path.with_suffix(".html")
        html = self.render(report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return path
