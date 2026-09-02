"""Deterministic aggregation of validated LAN player-map statistics."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable

from models.lan_match import PlayedMap, PlayedSeries, PlayerMapStatistics
from models.statistics import (
    MapStatistics,
    PlayerRawTotals,
    PlayerStatistics,
    SeriesStatistics,
    TournamentStatistics,
)
from models.tournament_import import ImportedSeries, TournamentImportResult


def _map_key(played_map: PlayedMap) -> tuple[int, str, str]:
    return (played_map.mapnumber, played_map.matchid, str(played_map.source or ""))


def _aggregate_players(
    maps: Iterable[PlayedMap],
    *,
    series_played_by_player: dict[str, int],
    map_sort_key: Callable[[PlayedMap], tuple[object, ...]] = _map_key,
) -> tuple[PlayerStatistics, ...]:
    ordered_maps = tuple(sorted(maps, key=map_sort_key))
    records = _ordered_performances_in_order(ordered_maps)
    totals: dict[str, PlayerRawTotals] = defaultdict(PlayerRawTotals)
    aliases: dict[str, set[str]] = defaultdict(set)
    teams: dict[str, set[str]] = defaultdict(set)
    alias_counts: dict[str, Counter[str]] = defaultdict(Counter)
    map_counts: dict[str, int] = defaultdict(int)

    for played_map in ordered_maps:
        for record in sorted(played_map.performances, key=lambda item: item.player_id):
            map_counts[record.player_id] += 1
    for record in records:
        player_id = record.player_id
        totals[player_id] = totals[player_id] + PlayerRawTotals.from_performance(record)
        aliases[player_id].add(record.name)
        alias_counts[player_id][record.name] += 1
        teams[player_id].add(record.team)

    return tuple(
        PlayerStatistics(
            player_id=player_id,
            display_name=min(
                alias
                for alias, count in alias_counts[player_id].items()
                if count == max(alias_counts[player_id].values())
            ),
            observed_aliases=tuple(sorted(aliases[player_id], key=lambda item: (item.casefold(), item))),
            observed_teams=tuple(sorted(teams[player_id], key=lambda item: (item.casefold(), item))),
            maps_played=map_counts[player_id],
            series_played=series_played_by_player[player_id],
            raw=totals[player_id],
        )
        for player_id in sorted(totals)
    )


def _ordered_performances_in_order(
    maps: Iterable[PlayedMap],
) -> list[PlayerMapStatistics]:
    performances: list[PlayerMapStatistics] = []
    for played_map in maps:
        player_ids = [item.player_id for item in played_map.performances]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError(
                f"map {played_map.series_id}/{played_map.mapnumber} contains duplicate players"
            )
        performances.extend(sorted(played_map.performances, key=lambda item: item.player_id))
    return performances


def aggregate_map(played_map: PlayedMap) -> MapStatistics:
    player_ids = {item.player_id for item in played_map.performances}
    players = _aggregate_players(
        (played_map,),
        series_played_by_player={player_id: 1 for player_id in player_ids},
    )
    return MapStatistics(
        series_id=played_map.series_id,
        matchid=played_map.matchid,
        mapnumber=played_map.mapnumber,
        players=players,
    )


def aggregate_series(series: ImportedSeries | PlayedSeries) -> SeriesStatistics:
    player_ids = {
        performance.player_id
        for played_map in series.maps
        for performance in played_map.performances
    }
    players = _aggregate_players(
        series.maps,
        series_played_by_player={player_id: 1 for player_id in player_ids},
    )
    return SeriesStatistics(
        series_id=series.series_id,
        best_of=series.best_of,
        maps_played=len(series.maps),
        players=players,
    )


def aggregate_tournament(result: TournamentImportResult) -> TournamentStatistics:
    """Aggregate SCRUM-19's accepted, tournament-wide deduplicated map set."""
    fingerprints = [item.fingerprint for item in result.imported_files]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("tournament import contains duplicate accepted map fingerprints")
    maps = tuple(item.played_map for item in result.imported_files)
    series_by_player: dict[str, set[str]] = defaultdict(set)
    for played_map in maps:
        for performance in played_map.performances:
            series_by_player[performance.player_id].add(played_map.series_id)
    players = _aggregate_players(
        maps,
        series_played_by_player={
            player_id: len(series_ids) for player_id, series_ids in series_by_player.items()
        },
        map_sort_key=lambda item: (
            item.series_id.casefold(),
            item.series_id,
            *_map_key(item),
        ),
    )
    return TournamentStatistics(
        series_count=len({played_map.series_id for played_map in maps}),
        map_count=len(maps),
        players=players,
    )
