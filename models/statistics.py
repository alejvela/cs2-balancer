"""Immutable raw and derived player statistics at every aggregation level."""

from __future__ import annotations

from dataclasses import dataclass, fields

from models.lan_match import BestOf, PlayerMapStatistics


def safe_ratio(numerator: int, denominator: int) -> float:
    """Return a finite ratio, using zero for an absent denominator."""
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True, slots=True)
class PlayerRawTotals:
    kills: int = 0
    deaths: int = 0
    damage: int = 0
    assists: int = 0
    enemy5ks: int = 0
    enemy4ks: int = 0
    enemy3ks: int = 0
    enemy2ks: int = 0
    utility_count: int = 0
    utility_damage: int = 0
    utility_successes: int = 0
    utility_enemies: int = 0
    flash_count: int = 0
    flash_successes: int = 0
    health_points_removed_total: int = 0
    health_points_dealt_total: int = 0
    shots_fired_total: int = 0
    shots_on_target_total: int = 0
    v1_count: int = 0
    v1_wins: int = 0
    v2_count: int = 0
    v2_wins: int = 0
    entry_count: int = 0
    entry_wins: int = 0
    equipment_value: int = 0
    money_saved: int = 0
    kill_reward: int = 0
    live_time: int = 0
    head_shot_kills: int = 0
    cash_earned: int = 0
    enemies_flashed: int = 0

    @classmethod
    def from_performance(cls, performance: PlayerMapStatistics) -> PlayerRawTotals:
        return cls(**{field.name: getattr(performance, field.name) for field in fields(cls)})

    def __add__(self, other: PlayerRawTotals) -> PlayerRawTotals:
        if not isinstance(other, PlayerRawTotals):
            return NotImplemented
        return type(self)(
            **{
                field.name: getattr(self, field.name) + getattr(other, field.name)
                for field in fields(self)
            }
        )


RAW_ADDITIVE_FIELDS = tuple(field.name for field in fields(PlayerRawTotals))


@dataclass(frozen=True, slots=True)
class PlayerStatistics:
    player_id: str
    display_name: str
    observed_aliases: tuple[str, ...]
    observed_teams: tuple[str, ...]
    maps_played: int
    series_played: int
    raw: PlayerRawTotals

    @property
    def kd_ratio(self) -> float:
        return self.raw.kills / max(self.raw.deaths, 1)

    @property
    def kills_per_map(self) -> float:
        return safe_ratio(self.raw.kills, self.maps_played)

    @property
    def deaths_per_map(self) -> float:
        return safe_ratio(self.raw.deaths, self.maps_played)

    @property
    def damage_per_map(self) -> float:
        return safe_ratio(self.raw.damage, self.maps_played)

    @property
    def assists_per_map(self) -> float:
        return safe_ratio(self.raw.assists, self.maps_played)

    @property
    def headshot_rate(self) -> float:
        return safe_ratio(self.raw.head_shot_kills, self.raw.kills)

    @property
    def accuracy(self) -> float:
        return safe_ratio(self.raw.shots_on_target_total, self.raw.shots_fired_total)

    @property
    def entry_success_rate(self) -> float:
        return safe_ratio(self.raw.entry_wins, self.raw.entry_count)

    @property
    def v1_clutch_success_rate(self) -> float:
        return safe_ratio(self.raw.v1_wins, self.raw.v1_count)

    @property
    def v2_clutch_success_rate(self) -> float:
        return safe_ratio(self.raw.v2_wins, self.raw.v2_count)

    @property
    def supported_clutch_attempts(self) -> int:
        return self.raw.v1_count + self.raw.v2_count

    @property
    def supported_clutch_wins(self) -> int:
        return self.raw.v1_wins + self.raw.v2_wins

    @property
    def supported_clutch_success_rate(self) -> float:
        return safe_ratio(self.supported_clutch_wins, self.supported_clutch_attempts)

    @property
    def flash_success_rate(self) -> float:
        return safe_ratio(self.raw.flash_successes, self.raw.flash_count)

    @property
    def enemies_flashed_per_flash(self) -> float:
        return safe_ratio(self.raw.enemies_flashed, self.raw.flash_count)

    @property
    def utility_success_rate(self) -> float:
        return safe_ratio(self.raw.utility_successes, self.raw.utility_count)

    @property
    def utility_damage_per_use(self) -> float:
        return safe_ratio(self.raw.utility_damage, self.raw.utility_count)

    @property
    def utility_damage_per_map(self) -> float:
        return safe_ratio(self.raw.utility_damage, self.maps_played)

    @property
    def enemies_flashed_per_map(self) -> float:
        return safe_ratio(self.raw.enemies_flashed, self.maps_played)

    @property
    def entry_attempts_per_map(self) -> float:
        return safe_ratio(self.raw.entry_count, self.maps_played)

    @property
    def multikill_events(self) -> int:
        return self.raw.enemy2ks + self.raw.enemy3ks + self.raw.enemy4ks + self.raw.enemy5ks

    @property
    def multikill_events_per_map(self) -> float:
        return safe_ratio(self.multikill_events, self.maps_played)


@dataclass(frozen=True, slots=True)
class MapStatistics:
    series_id: str
    matchid: str
    mapnumber: int
    players: tuple[PlayerStatistics, ...]


@dataclass(frozen=True, slots=True)
class SeriesStatistics:
    series_id: str
    best_of: BestOf | None
    maps_played: int
    players: tuple[PlayerStatistics, ...]


@dataclass(frozen=True, slots=True)
class TournamentStatistics:
    series_count: int
    map_count: int
    players: tuple[PlayerStatistics, ...]
