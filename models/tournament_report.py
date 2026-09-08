"""Immutable presentation data composed from existing tournament contracts."""

from dataclasses import dataclass

from models.lan_match import BestOf
from models.player_merit import PlayerMerit, TournamentMerits
from models.player_ranking import PlayerRanking, PlayerRankingEntry
from models.statistics import TournamentStatistics
from models.tournament_import import TournamentImportResult


@dataclass(frozen=True, slots=True)
class ReportMetric:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class PlayerReport:
    entry: PlayerRankingEntry
    metrics: tuple[ReportMetric, ...]
    merits: tuple[PlayerMerit, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "merits", tuple(self.merits))


@dataclass(frozen=True, slots=True)
class LeaderboardReport:
    ranking: PlayerRanking
    players: tuple[PlayerReport, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "players", tuple(self.players))
        if tuple(player.entry for player in self.players) != self.ranking.entries:
            raise ValueError("report must preserve the supplied ranking exactly")


@dataclass(frozen=True, slots=True)
class MapReport:
    mapnumber: int
    matchid: str
    source: str
    leaderboard: LeaderboardReport


@dataclass(frozen=True, slots=True)
class SeriesReport:
    series_id: str
    display_name: str
    best_of: BestOf | None
    accepted: bool
    leaderboard: LeaderboardReport
    maps: tuple[MapReport, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "maps", tuple(self.maps))


@dataclass(frozen=True, slots=True)
class TournamentReport:
    title: str
    import_result: TournamentImportResult
    statistics: TournamentStatistics
    leaderboard: LeaderboardReport
    merits: TournamentMerits
    series: tuple[SeriesReport, ...]
    empty_folders: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "series", tuple(self.series))
        object.__setattr__(self, "empty_folders", tuple(self.empty_folders))

    @property
    def mvp(self) -> PlayerReport | None:
        """First eligible ranked player; no competitive formula of our own."""
        return next(
            (
                player
                for player in self.leaderboard.players
                if player.entry.tournament_eligibility is not None
                and player.entry.tournament_eligibility.eligible
            ),
            None,
        )
