from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalSearchProblem:
    """
    Problema preparado para la búsqueda GLOBAL.

    Contiene toda la información necesaria para empezar
    branch & bound:

        - jugadores ya ordenados;
        - nodo raíz canónico;
        - número de equipos;
        - tamaño de equipo;
        - configuración de seeds protegidos.

    Los índices almacenados en GlobalSearchState hacen referencia
    directamente a `players`.
    """

    players: tuple[
        GlobalPlayerMetrics,
        ...
    ]

    root_state: GlobalSearchState

    number_of_teams: int

    team_size: int

    protected_seed_level: int | None = 1

    maximum_protected_seeds_per_team: int = 1

    def __post_init__(
        self,
    ) -> None:
        players = tuple(
            self.players
        )

        if not players:
            raise ValueError(
                "players cannot be empty."
            )

        if any(
            not isinstance(
                player,
                GlobalPlayerMetrics,
            )
            for player in players
        ):
            raise TypeError(
                "players must contain "
                "GlobalPlayerMetrics instances."
            )

        object.__setattr__(
            self,
            "players",
            players,
        )

        if not isinstance(
            self.root_state,
            GlobalSearchState,
        ):
            raise TypeError(
                "root_state must be a GlobalSearchState."
            )

        if (
            isinstance(
                self.number_of_teams,
                bool,
            )
            or not isinstance(
                self.number_of_teams,
                int,
            )
        ):
            raise TypeError(
                "number_of_teams must be an integer."
            )

        if self.number_of_teams <= 0:
            raise ValueError(
                "number_of_teams must be greater than zero."
            )

        if (
            isinstance(
                self.team_size,
                bool,
            )
            or not isinstance(
                self.team_size,
                int,
            )
        ):
            raise TypeError(
                "team_size must be an integer."
            )

        if self.team_size <= 0:
            raise ValueError(
                "team_size must be greater than zero."
            )

        if (
            self.root_state.team_count
            != self.number_of_teams
        ):
            raise ValueError(
                "root_state team count does not match "
                "number_of_teams."
            )

        expected_player_count = (
            self.number_of_teams
            * self.team_size
        )

        if len(
            players
        ) != expected_player_count:
            raise ValueError(
                "GLOBAL currently requires exactly "
                f"{expected_player_count} players. "
                f"Received {len(players)}."
            )

        if (
            isinstance(
                self.maximum_protected_seeds_per_team,
                bool,
            )
            or not isinstance(
                self.maximum_protected_seeds_per_team,
                int,
            )
        ):
            raise TypeError(
                "maximum_protected_seeds_per_team "
                "must be an integer."
            )

        if (
            self.maximum_protected_seeds_per_team
            < 0
        ):
            raise ValueError(
                "maximum_protected_seeds_per_team "
                "cannot be negative."
            )

        if (
            self.root_state.next_player_index
            != self.root_state.assigned_count
        ):
            raise ValueError(
                "The root state must use a sequential "
                "player assignment order."
            )

        if (
            self.root_state.assigned_count
            > len(players)
        ):
            raise ValueError(
                "root_state assigns more players "
                "than the problem contains."
            )

    @property
    def player_count(
        self,
    ) -> int:
        return len(
            self.players
        )

    @property
    def remaining_player_count(
        self,
    ) -> int:
        return (
            self.player_count
            - self.root_state.assigned_count
        )

    @property
    def preassigned_player_count(
        self,
    ) -> int:
        return (
            self.root_state.assigned_count
        )

    @property
    def is_root_complete(
        self,
    ) -> bool:
        return self.root_state.is_complete(
            self.player_count
        )

    def player_at(
        self,
        index: int,
    ) -> GlobalPlayerMetrics:
        if (
            isinstance(
                index,
                bool,
            )
            or not isinstance(
                index,
                int,
            )
        ):
            raise TypeError(
                "index must be an integer."
            )

        if not (
            0
            <= index
            < len(
                self.players
            )
        ):
            raise IndexError(
                f"Invalid player index {index}."
            )

        return self.players[
            index
        ]

    def next_player(
        self,
        state: GlobalSearchState,
    ) -> GlobalPlayerMetrics | None:
        """
        Devuelve el jugador que corresponde expandir desde `state`.
        """
        if state.is_complete(
            self.player_count
        ):
            return None

        return self.player_at(
            state.next_player_index
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "player_count": (
                self.player_count
            ),

            "number_of_teams": (
                self.number_of_teams
            ),

            "team_size": (
                self.team_size
            ),

            "protected_seed_level": (
                self.protected_seed_level
            ),

            "maximum_protected_seeds_per_team": (
                self.maximum_protected_seeds_per_team
            ),

            "preassigned_player_count": (
                self.preassigned_player_count
            ),

            "remaining_player_count": (
                self.remaining_player_count
            ),

            "root_state": (
                self.root_state.as_dict()
            ),

            "player_order": [
                {
                    "index": index,
                    "nickname": (
                        player.nickname
                    ),
                    "power": (
                        player.power
                    ),
                    "elo": (
                        player.elo
                    ),
                    "kd": (
                        player.kd
                    ),
                    "seed": (
                        player.seed
                    ),
                }
                for index, player
                in enumerate(
                    self.players
                )
            ],
        }

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"players={self.player_count}, "
            f"teams={self.number_of_teams}, "
            f"team_size={self.team_size}, "
            f"preassigned="
            f"{self.preassigned_player_count})"
        )
