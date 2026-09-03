"""Application service for deterministic LAN player rankings."""

from __future__ import annotations

from collections.abc import Callable

from application.player_impact import (
    LAN_IMPACT_VERSION,
    calculate_player_impact,
    impact_tie_break_key,
    tournament_impact_eligibility,
)
from application.statistics_aggregation import (
    aggregate_map,
    aggregate_series,
    aggregate_tournament,
)
from models.lan_match import PlayedMap, PlayedSeries
from models.player_impact import TournamentImpactEligibility
from models.player_ranking import (
    PlayerRanking,
    PlayerRankingEntry,
    RankingScope,
)
from models.statistics import PlayerStatistics
from models.tournament_import import ImportedSeries, TournamentImportResult


def map_ranking_context_id(played_map: PlayedMap) -> str:
    return (
        f"series={played_map.series_id};match={played_map.matchid};"
        f"map={played_map.mapnumber}"
    )


def _rank_players(
    players: tuple[PlayerStatistics, ...],
    *,
    scope: RankingScope,
    context_id: str,
    eligibility_for: Callable[[PlayerStatistics], TournamentImpactEligibility | None],
) -> PlayerRanking:
    evaluated = [(statistics, calculate_player_impact(statistics)) for statistics in players]
    evaluated.sort(key=lambda item: impact_tie_break_key(item[1], item[0]))
    entries = tuple(
        PlayerRankingEntry(
            rank=rank,
            player_id=statistics.player_id,
            display_name=statistics.display_name,
            observed_aliases=statistics.observed_aliases,
            observed_teams=statistics.observed_teams,
            scope=scope,
            context_id=context_id,
            maps_played=statistics.maps_played,
            series_played=statistics.series_played,
            statistics=statistics,
            impact=impact,
            tournament_eligibility=eligibility_for(statistics),
        )
        for rank, (statistics, impact) in enumerate(evaluated, start=1)
    )
    return PlayerRanking(scope, context_id, entries, LAN_IMPACT_VERSION)


def rank_map(played_map: PlayedMap) -> PlayerRanking:
    aggregated = aggregate_map(played_map)
    return _rank_players(
        aggregated.players,
        scope=RankingScope.MAP,
        context_id=map_ranking_context_id(played_map),
        eligibility_for=lambda _: None,
    )


def rank_series(series: ImportedSeries | PlayedSeries) -> PlayerRanking:
    aggregated = aggregate_series(series)
    return _rank_players(
        aggregated.players,
        scope=RankingScope.SERIES,
        context_id=series.series_id,
        eligibility_for=lambda _: None,
    )


def rank_tournament(
    result: TournamentImportResult,
    *,
    tournament_id: str,
) -> PlayerRanking:
    if not tournament_id:
        raise ValueError("tournament_id cannot be empty")
    aggregated = aggregate_tournament(result)
    maximum_maps = max((item.maps_played for item in aggregated.players), default=0)
    return _rank_players(
        aggregated.players,
        scope=RankingScope.TOURNAMENT,
        context_id=tournament_id,
        eligibility_for=lambda statistics: tournament_impact_eligibility(
            statistics, maximum_maps
        ),
    )
