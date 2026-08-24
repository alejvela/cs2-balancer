from dataclasses import dataclass, field

from models.player import Player
from models.team_statistics import TeamStatistics


@dataclass(slots=True)
class Team:

    id: int

    players: list[Player] = field(default_factory=list)

    statistics: TeamStatistics = field(init=False)

    def __post_init__(self):

        self.statistics = TeamStatistics(self)

    def add(self, player: Player):

        self.players.append(player)
        self.statistics.invalidate()

    def remove(self, player: Player):

        self.players.remove(player)
        self.statistics.invalidate()

    @property
    def size(self):

        return len(self.players)

    def __iter__(self):

        return iter(self.players)

    def __len__(self):

        return len(self.players)
