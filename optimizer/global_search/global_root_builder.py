from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from optimizer.global_search.global_player_ordering import (
    GlobalPlayerOrdering,
)
from optimizer.global_search.global_search_problem import (
    GlobalSearchProblem,
)
from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
    GlobalSearchState,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalRootBuilder:
    """
    Construye el problema inicial de búsqueda GLOBAL.

    Su responsabilidad principal es eliminar simetrías antes
    de comenzar branch & bound.

    ============================================================
    Seeds protegidos
    ============================================================

    Si existen jugadores con:

        seed == protected_seed_level

    se colocan canónicamente al principio de los equipos.

    Ejemplo con cuatro Seed 1:

        Seed A → Team 0
        Seed B → Team 1
        Seed C → Team 2
        Seed D → Team 3

    Las asignaciones equivalentes por permutación:

        A→T1 B→T0 C→T2 D→T3
        A→T2 B→T0 C→T1 D→T3
        ...

    no necesitan explorarse.

    ============================================================
    Orden de jugadores
    ============================================================

    Los seeds protegidos ocupan siempre las primeras posiciones
    del vector global.

    Después se utiliza GlobalPlayerOrdering para ordenar los
    jugadores restantes por influencia/extremidad.

    Por tanto:

        root_state.next_player_index

    siempre coincide con el siguiente elemento de:

        problem.players
    """

    number_of_teams: int

    team_size: int

    protected_seed_level: int | None = 1

    maximum_protected_seeds_per_team: int = 1

    def __post_init__(
        self,
    ) -> None:
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

        if self.protected_seed_level is not None:
            if (
                isinstance(
                    self.protected_seed_level,
                    bool,
                )
                or not isinstance(
                    self.protected_seed_level,
                    int,
                )
            ):
                raise TypeError(
                    "protected_seed_level must be "
                    "an integer or None."
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

    # ========================================================
    # Construcción
    # ========================================================

    def build(
        self,
        players: Sequence[
            GlobalPlayerMetrics
        ],
        ordering: GlobalPlayerOrdering | None = None,
    ) -> GlobalSearchProblem:
        player_list = self._validate_players(
            players
        )

        expected_player_count = (
            self.number_of_teams
            * self.team_size
        )

        if len(
            player_list
        ) != expected_player_count:
            raise ValueError(
                "GLOBAL requires exactly "
                f"{expected_player_count} players. "
                f"Received {len(player_list)}."
            )

        ordering = (
            ordering
            if ordering is not None
            else GlobalPlayerOrdering(
                protected_seed_level=(
                    self.protected_seed_level
                )
            )
        )

        protected_players = [
            player
            for player in player_list
            if self._is_protected_seed(
                player
            )
        ]

        normal_players = [
            player
            for player in player_list
            if not self._is_protected_seed(
                player
            )
        ]

        self._validate_seed_feasibility(
            protected_players
        )

        # ----------------------------------------------------
        # Orden determinista de seeds
        # ----------------------------------------------------

        protected_players = list(
            ordering.order(
                protected_players
            )
        ) if protected_players else []

        # ----------------------------------------------------
        # Orden determinista del resto
        # ----------------------------------------------------

        normal_players = list(
            ordering.order(
                normal_players
            )
        ) if normal_players else []

        # Los seeds van primero para poder construir un root_state
        # secuencial:
        #
        #   next_player_index == assigned_count
        #
        ordered_players = tuple(
            protected_players
            + normal_players
        )

        root_state = (
            GlobalSearchState.empty(
                number_of_teams=(
                    self.number_of_teams
                )
            )
        )

        # ====================================================
        # Fijación canónica de seeds
        # ====================================================

        root_state = (
            self._assign_protected_seeds(
                state=root_state,
                players=ordered_players,
                protected_count=(
                    len(
                        protected_players
                    )
                ),
            )
        )

        if not root_state.validate_capacity_feasibility(
            total_player_count=(
                len(
                    ordered_players
                )
            ),
            team_size=self.team_size,
        ):
            raise RuntimeError(
                "The canonical root state has "
                "insufficient remaining capacity."
            )

        return GlobalSearchProblem(
            players=ordered_players,

            root_state=(
                root_state
            ),

            number_of_teams=(
                self.number_of_teams
            ),

            team_size=(
                self.team_size
            ),

            protected_seed_level=(
                self.protected_seed_level
            ),

            maximum_protected_seeds_per_team=(
                self.maximum_protected_seeds_per_team
            ),
        )

    # ========================================================
    # Seeds
    # ========================================================

    def _assign_protected_seeds(
        self,
        state: GlobalSearchState,
        players: tuple[
            GlobalPlayerMetrics,
            ...
        ],
        protected_count: int,
    ) -> GlobalSearchState:
        """
        Coloca los seeds protegidos de forma canónica.

        Con máximo 1 seed por equipo:

            seed 0 → team 0
            seed 1 → team 1
            seed 2 → team 2
            ...

        Para configuraciones con más de un seed permitido por equipo,
        se distribuyen por rondas:

            seed 0 → T0
            seed 1 → T1
            seed 2 → T2
            seed 3 → T3
            seed 4 → T0
            ...
        """

        current = state

        for seed_index in range(
            protected_count
        ):
            metrics = players[
                current.next_player_index
            ]

            team_index = (
                seed_index
                % self.number_of_teams
            )

            current = (
                current.assign_next_player(
                    team_index=team_index,

                    metrics=metrics,

                    team_size=(
                        self.team_size
                    ),

                    protected_seed_level=(
                        self.protected_seed_level
                    ),

                    maximum_protected_seeds_per_team=(
                        self.maximum_protected_seeds_per_team
                    ),
                )
            )

        return current

    def _is_protected_seed(
        self,
        player: GlobalPlayerMetrics,
    ) -> bool:
        return (
            self.protected_seed_level
            is not None
            and player.seed
            == self.protected_seed_level
        )

    def _validate_seed_feasibility(
        self,
        protected_players: Sequence[
            GlobalPlayerMetrics
        ],
    ) -> None:
        protected_count = len(
            protected_players
        )

        maximum_capacity = (
            self.number_of_teams
            * self.maximum_protected_seeds_per_team
        )

        if (
            protected_count
            > maximum_capacity
        ):
            raise ValueError(
                "The protected seed constraint "
                "is impossible to satisfy. "
                f"Protected players: {protected_count}. "
                f"Maximum capacity: {maximum_capacity}."
            )

        if (
            protected_count > 0
            and self.maximum_protected_seeds_per_team
            <= 0
        ):
            raise ValueError(
                "Protected seed players exist but "
                "maximum_protected_seeds_per_team is zero."
            )

    # ========================================================
    # Validación
    # ========================================================

    @staticmethod
    def _validate_players(
        players: Sequence[
            GlobalPlayerMetrics
        ],
    ) -> list[
        GlobalPlayerMetrics
    ]:
        if players is None:
            raise ValueError(
                "players cannot be None."
            )

        player_list = list(
            players
        )

        if not player_list:
            raise ValueError(
                "At least one player is required."
            )

        for index, player in enumerate(
            player_list,
            start=1,
        ):
            if not isinstance(
                player,
                GlobalPlayerMetrics,
            ):
                raise TypeError(
                    "players must contain "
                    "GlobalPlayerMetrics instances. "
                    f"Invalid item at position {index}."
                )

        identities = [
            player.identity
            for player in player_list
        ]

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "players contains duplicated identities."
            )

        return player_list

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"teams={self.number_of_teams}, "
            f"team_size={self.team_size}, "
            f"protected_seed_level="
            f"{self.protected_seed_level!r}, "
            f"maximum_protected_seeds_per_team="
            f"{self.maximum_protected_seeds_per_team})"
        )
