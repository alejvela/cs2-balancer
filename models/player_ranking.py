"""Immutable, presentation-independent LAN player ranking results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from models.player_impact import PlayerImpactResult, TournamentImpactEligibility
from models.statistics import PlayerStatistics


class RankingScope(StrEnum):
    MAP = "map"
    SERIES = "series"
    TOURNAMENT = "tournament"


@dataclass(frozen=True, slots=True)
class PlayerRankingEntry:
    rank: int
    player_id: str
    display_name: str
    observed_aliases: tuple[str, ...]
    observed_teams: tuple[str, ...]
    scope: RankingScope
    context_id: str
    maps_played: int
    series_played: int
    statistics: PlayerStatistics
    impact: PlayerImpactResult
    tournament_eligibility: TournamentImpactEligibility | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_aliases", tuple(self.observed_aliases))
        object.__setattr__(self, "observed_teams", tuple(self.observed_teams))
        if self.rank < 1:
            raise ValueError("rank must be at least 1")
        if not self.context_id:
            raise ValueError("context_id cannot be empty")
        if self.player_id != self.statistics.player_id or self.player_id != self.impact.player_id:
            raise ValueError("entry, statistics, and impact player ids must match")
        if self.display_name != self.statistics.display_name:
            raise ValueError("entry display name must match statistics")
        if self.observed_aliases != self.statistics.observed_aliases:
            raise ValueError("entry aliases must match statistics")
        if self.observed_teams != self.statistics.observed_teams:
            raise ValueError("entry teams must match statistics")
        if self.maps_played != self.statistics.maps_played:
            raise ValueError("entry maps_played must match statistics")
        if self.series_played != self.statistics.series_played:
            raise ValueError("entry series_played must match statistics")
        if self.scope is RankingScope.TOURNAMENT:
            if self.tournament_eligibility is None:
                raise ValueError("tournament ranking entries require eligibility")
        elif self.tournament_eligibility is not None:
            raise ValueError("eligibility is only valid for tournament rankings")


@dataclass(frozen=True, slots=True)
class PlayerRanking:
    scope: RankingScope
    context_id: str
    entries: tuple[PlayerRankingEntry, ...]
    model_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))
        if not self.context_id:
            raise ValueError("context_id cannot be empty")
        if [item.rank for item in self.entries] != list(range(1, len(self.entries) + 1)):
            raise ValueError("ranking entries must have contiguous ordinal ranks")
        player_ids = [item.player_id for item in self.entries]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("ranking player ids must be unique")
        if any(item.scope is not self.scope for item in self.entries):
            raise ValueError("entry scope must match ranking scope")
        if any(item.context_id != self.context_id for item in self.entries):
            raise ValueError("entry context must match ranking context")
        if any(item.impact.model_version != self.model_version for item in self.entries):
            raise ValueError("ranking and impact model versions must match")

        from application.player_impact import impact_tie_break_key

        keys = [impact_tie_break_key(item.impact, item.statistics) for item in self.entries]
        if keys != sorted(keys):
            raise ValueError("ranking entries must follow the canonical comparison order")
