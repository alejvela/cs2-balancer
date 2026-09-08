"""Compose the LAN statistics pipeline; keep all orchestration out of HTML."""

from collections.abc import Mapping
from pathlib import Path

from application.player_merits import generate_tournament_merits
from application.player_rankings import rank_map, rank_series, rank_tournament
from application.statistics_aggregation import aggregate_tournament
from importers.tournament_folder import import_tournament_folder
from models.player_merit import TournamentMerits
from models.player_ranking import PlayerRanking, PlayerRankingEntry
from models.tournament_import import TournamentImportResult
from models.tournament_report import (
    LeaderboardReport,
    MapReport,
    PlayerReport,
    ReportMetric,
    SeriesReport,
    TournamentReport,
)


def _player(entry: PlayerRankingEntry, merits: TournamentMerits) -> PlayerReport:
    stats, raw = entry.statistics, entry.statistics.raw
    # Read existing derived properties; denominator checks only control availability.
    derived = (
        ("K/D", stats.kd_ratio, True, False),
        ("Kills / map", stats.kills_per_map, stats.maps_played, False),
        ("Damage / map", stats.damage_per_map, stats.maps_played, False),
        ("Assists / map", stats.assists_per_map, stats.maps_played, False),
        ("Headshot rate", stats.headshot_rate, raw.kills, True),
        ("Accuracy", stats.accuracy, raw.shots_fired_total, True),
        ("Entry conversion", stats.entry_success_rate, raw.entry_count, True),
        (
            "Supported clutch conversion",
            stats.supported_clutch_success_rate,
            stats.supported_clutch_attempts,
            True,
        ),
        ("Flash conversion", stats.flash_success_rate, raw.flash_count, True),
        ("Utility conversion", stats.utility_success_rate, raw.utility_count, True),
    )
    metrics = tuple(
        ReportMetric(
            label, (f"{value:.1%}" if percent else f"{value:.2f}") if defined else "—"
        )
        for label, value, defined, percent in derived
    )
    return PlayerReport(
        entry,
        metrics,
        tuple(merit for merit in merits.merits if merit.player_id == entry.player_id),
    )


def _leaderboard(ranking: PlayerRanking, merits: TournamentMerits) -> LeaderboardReport:
    return LeaderboardReport(
        ranking, tuple(_player(entry, merits) for entry in ranking.entries)
    )


def build_tournament_report(
    imported: TournamentImportResult,
    *,
    tournament_id: str,
    title: str = "CS2 LAN · Informe del torneo",
) -> TournamentReport:
    """Reuse accepted deduplicated maps, including maps awaiting series metadata."""
    statistics = aggregate_tournament(imported)
    ranking = rank_tournament(imported, tournament_id=tournament_id)
    merits = generate_tournament_merits(statistics)
    accepted = {series.series_id: series for series in imported.series}
    series_reports = []
    for series in sorted(
        imported.imported_series,
        key=lambda item: (item.series_id.casefold(), item.series_id),
    ):
        accepted_series = accepted.get(series.series_id)
        maps = tuple(
            MapReport(
                item.mapnumber,
                item.matchid,
                str(item.source or "—"),
                _leaderboard(rank_map(item), TournamentMerits(())),
            )
            for item in sorted(series.maps, key=lambda item: item.mapnumber)
        )
        series_reports.append(
            SeriesReport(
                series.series_id,
                (accepted_series.display_name or series.series_id)
                if accepted_series
                else series.series_id,
                series.best_of,
                accepted_series is not None,
                _leaderboard(
                    rank_series(accepted_series or series), TournamentMerits(())
                ),
                maps,
            )
        )
    folders_with_maps = {series.folder for series in imported.imported_series}
    empty_folders = tuple(
        str(folder)
        for folder in sorted(
            imported.discovered_series_folders,
            key=lambda item: (str(item).casefold(), str(item)),
        )
        if folder not in folders_with_maps
    )
    return TournamentReport(
        title,
        imported,
        statistics,
        _leaderboard(ranking, merits),
        merits,
        tuple(series_reports),
        empty_folders,
    )


def generate_tournament_report(
    root: Path | str,
    output: Path | str,
    *,
    best_of_by_series: Mapping[str, object],
    tournament_id: str,
    title: str = "CS2 LAN · Informe del torneo",
) -> Path:
    """Folder -> validated import -> report -> standalone UTF-8 HTML file."""
    from exporters.tournament_html import TournamentHtmlExporter

    imported = import_tournament_folder(root, best_of_by_series=best_of_by_series)
    report = build_tournament_report(imported, tournament_id=tournament_id, title=title)
    return TournamentHtmlExporter().export(report, output)
