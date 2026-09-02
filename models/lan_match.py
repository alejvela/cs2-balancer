"""Domain objects for raw statistics produced by a played LAN match."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import IntEnum
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PlayerMapStatistics:
    """One immutable, lossless row from the supported map CSV export."""

    matchid: str
    mapnumber: int
    steamid64: str
    team: str
    name: str
    kills: int
    deaths: int
    damage: int
    assists: int
    enemy5ks: int
    enemy4ks: int
    enemy3ks: int
    enemy2ks: int
    utility_count: int
    utility_damage: int
    utility_successes: int
    utility_enemies: int
    flash_count: int
    flash_successes: int
    health_points_removed_total: int
    health_points_dealt_total: int
    shots_fired_total: int
    shots_on_target_total: int
    v1_count: int
    v1_wins: int
    v2_count: int
    v2_wins: int
    entry_count: int
    entry_wins: int
    equipment_value: int
    money_saved: int
    kill_reward: int
    live_time: int
    head_shot_kills: int
    cash_earned: int
    enemies_flashed: int

    @property
    def player_id(self) -> str:
        """Canonical identity; nickname changes do not affect it."""
        return self.steamid64

    def as_dict(self) -> dict[str, str | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True, slots=True)
class PlayedMap:
    """A map export and the filesystem series boundary it came from."""

    series_id: str
    matchid: str
    mapnumber: int
    performances: tuple[PlayerMapStatistics, ...]
    source: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "performances", tuple(self.performances))
        if not self.series_id.strip():
            raise ValueError("series_id cannot be empty")
        if not self.performances:
            raise ValueError("a played map must contain player performances")
        for performance in self.performances:
            if performance.matchid != self.matchid:
                raise ValueError("all performances must have the map matchid")
            if performance.mapnumber != self.mapnumber:
                raise ValueError("all performances must have the mapnumber")


class BestOf(IntEnum):
    BO1 = 1
    BO3 = 3
    BO5 = 5


@dataclass(frozen=True, slots=True)
class PlayedSeries:
    """Maps played within one authoritative filesystem subfolder."""

    series_id: str
    best_of: BestOf
    maps: tuple[PlayedMap, ...]
    display_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "maps", tuple(self.maps))
        if not self.series_id.strip():
            raise ValueError("series_id cannot be empty")
        if not self.maps:
            raise ValueError("a played series must contain at least one map")
        if len(self.maps) > self.best_of:
            raise ValueError(f"{self.best_of.name} cannot contain {len(self.maps)} maps")
        if any(played_map.series_id != self.series_id for played_map in self.maps):
            raise ValueError("maps from different series folders cannot be combined")
        mapnumbers = [played_map.mapnumber for played_map in self.maps]
        if len(mapnumbers) != len(set(mapnumbers)):
            raise ValueError("mapnumber must be unique within a series")
        object.__setattr__(self, "maps", tuple(sorted(self.maps, key=lambda item: item.mapnumber)))


@dataclass(frozen=True, slots=True)
class Tournament:
    """Minimal container boundary; intentionally performs no aggregation."""

    tournament_id: str
    series: tuple[PlayedSeries, ...]
    display_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "series", tuple(self.series))
        if not self.tournament_id.strip():
            raise ValueError("tournament_id cannot be empty")
        identifiers = [played_series.series_id for played_series in self.series]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("series_id must be unique within a tournament")
