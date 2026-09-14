"""Execution data for the public balancing application boundary."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from models.player import Player
from optimizer.modes.optimization_mode import OptimizationMode


@dataclass(frozen=True, slots=True)
class BalancingRequest:
    """Snapshot the player collection and top-level metadata, not Player objects."""

    players: Sequence[Player]
    number_of_teams: int
    optimization_mode: OptimizationMode
    title: str | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.players is None:
            raise TypeError("players cannot be None")
        players = tuple(self.players)
        if not players:
            raise ValueError("players cannot be empty")
        if isinstance(self.number_of_teams, bool) or not isinstance(
            self.number_of_teams, int
        ):
            raise TypeError("number_of_teams must be an integer")
        if self.number_of_teams <= 0:
            raise ValueError("number_of_teams must be positive")
        if not isinstance(self.optimization_mode, OptimizationMode):
            raise TypeError("optimization_mode must be an OptimizationMode")
        if self.title is not None and not isinstance(self.title, str):
            raise TypeError("title must be a string or None")
        if self.metadata is not None and not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping or None")
        object.__setattr__(self, "players", players)
        object.__setattr__(
            self, "metadata", MappingProxyType(dict(self.metadata or {}))
        )
