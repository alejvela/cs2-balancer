from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any

from models.player import Player


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalPlayerMetrics:
    """
    Métricas precalculadas de un jugador utilizadas por la búsqueda global.

    La búsqueda no debe recalcular ScoringModel.power(player) en cada nodo.

    power:
        Power final del jugador, incluyendo actividad.

    elo:
        ELO FACEIT utilizado por las restricciones de ELO.

    kd:
        KD utilizado por KD Balance.

    seed:
        Seed manual/configurada del jugador.

    player:
        Referencia a la instancia Player original.
    """

    player: Player

    power: float

    elo: float

    kd: float

    seed: int | None

    def __post_init__(
        self,
    ) -> None:
        if self.player is None:
            raise ValueError(
                "player cannot be None."
            )

        object.__setattr__(
            self,
            "power",
            self._validate_metric(
                self.power,
                "power",
            ),
        )

        object.__setattr__(
            self,
            "elo",
            self._validate_metric(
                self.elo,
                "elo",
            ),
        )

        object.__setattr__(
            self,
            "kd",
            self._validate_metric(
                self.kd,
                "kd",
            ),
        )

        if self.seed is not None:
            if (
                isinstance(
                    self.seed,
                    bool,
                )
                or not isinstance(
                    self.seed,
                    int,
                )
            ):
                raise TypeError(
                    "seed must be an integer or None."
                )

            if self.seed < 0:
                raise ValueError(
                    "seed cannot be negative."
                )

    @property
    def nickname(
        self,
    ) -> str:
        value = getattr(
            self.player,
            "nickname",
            getattr(
                self.player,
                "nick",
                None,
            ),
        )

        if value is None:
            return (
                f"Player-{id(self.player)}"
            )

        return str(value)

    @property
    def steam_id(
        self,
    ) -> str | None:
        value = getattr(
            self.player,
            "steam_id",
            None,
        )

        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return (
            normalized
            if normalized
            else None
        )

    @property
    def identity(
        self,
    ) -> tuple[str, str]:
        if self.steam_id is not None:
            return (
                "steam",
                self.steam_id,
            )

        return (
            "nickname",
            self.nickname
            .strip()
            .casefold(),
        )

    @staticmethod
    def _validate_metric(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                Real,
            )
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        numeric = float(
            value
        )

        if numeric < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return numeric


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalTeamState:
    """
    Estado parcial de un equipo dentro de un nodo de búsqueda.

    Se guardan únicamente datos necesarios para poda y construcción.

    No contiene un Team real.

    Esto evita:

        - crear objetos Team continuamente;
        - recalcular TeamStatistics;
        - recalcular Power de jugadores;
        - invalidar caches durante branch & bound.
    """

    player_indices: tuple[int, ...] = ()

    player_count: int = 0

    power_sum: float = 0.0

    elo_sum: float = 0.0

    kd_sum: float = 0.0

    protected_seed_count: int = 0

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.player_count,
                bool,
            )
            or not isinstance(
                self.player_count,
                int,
            )
        ):
            raise TypeError(
                "player_count must be an integer."
            )

        if self.player_count < 0:
            raise ValueError(
                "player_count cannot be negative."
            )

        if (
            self.player_count
            != len(
                self.player_indices
            )
        ):
            raise ValueError(
                "player_count must match "
                "len(player_indices)."
            )

        if (
            isinstance(
                self.protected_seed_count,
                bool,
            )
            or not isinstance(
                self.protected_seed_count,
                int,
            )
        ):
            raise TypeError(
                "protected_seed_count must be an integer."
            )

        if self.protected_seed_count < 0:
            raise ValueError(
                "protected_seed_count cannot be negative."
            )

        for field_name in (
            "power_sum",
            "elo_sum",
            "kd_sum",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    Real,
                )
            ):
                raise TypeError(
                    f"{field_name} must be numeric."
                )

    @property
    def is_empty(
        self,
    ) -> bool:
        return (
            self.player_count == 0
        )

    def remaining_capacity(
        self,
        team_size: int,
    ) -> int:
        if (
            isinstance(
                team_size,
                bool,
            )
            or not isinstance(
                team_size,
                int,
            )
        ):
            raise TypeError(
                "team_size must be an integer."
            )

        if team_size <= 0:
            raise ValueError(
                "team_size must be greater than zero."
            )

        return (
            team_size
            - self.player_count
        )

    @property
    def average_power(
        self,
    ) -> float:
        if self.player_count <= 0:
            return 0.0

        return (
            self.power_sum
            / self.player_count
        )

    @property
    def average_elo(
        self,
    ) -> float:
        if self.player_count <= 0:
            return 0.0

        return (
            self.elo_sum
            / self.player_count
        )

    @property
    def average_kd(
        self,
    ) -> float:
        if self.player_count <= 0:
            return 0.0

        return (
            self.kd_sum
            / self.player_count
        )

    def add_player(
        self,
        player_index: int,
        metrics: GlobalPlayerMetrics,
        protected_seed_level: int | None,
    ) -> GlobalTeamState:
        """
        Devuelve un nuevo estado de equipo con el jugador añadido.

        GlobalSearchState es inmutable, por lo que nunca modificamos
        un nodo existente.
        """
        if (
            isinstance(
                player_index,
                bool,
            )
            or not isinstance(
                player_index,
                int,
            )
        ):
            raise TypeError(
                "player_index must be an integer."
            )

        if player_index < 0:
            raise ValueError(
                "player_index cannot be negative."
            )

        if metrics is None:
            raise ValueError(
                "metrics cannot be None."
            )

        protected_seed = (
            protected_seed_level is not None
            and metrics.seed
            == protected_seed_level
        )

        return GlobalTeamState(
            player_indices=(
                self.player_indices
                + (
                    player_index,
                )
            ),

            player_count=(
                self.player_count
                + 1
            ),

            power_sum=(
                self.power_sum
                + metrics.power
            ),

            elo_sum=(
                self.elo_sum
                + metrics.elo
            ),

            kd_sum=(
                self.kd_sum
                + metrics.kd
            ),

            protected_seed_count=(
                self.protected_seed_count
                + (
                    1
                    if protected_seed
                    else 0
                )
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "player_indices": list(
                self.player_indices
            ),

            "player_count": (
                self.player_count
            ),

            "power_sum": (
                self.power_sum
            ),

            "elo_sum": (
                self.elo_sum
            ),

            "kd_sum": (
                self.kd_sum
            ),

            "average_power": (
                self.average_power
            ),

            "average_elo": (
                self.average_elo
            ),

            "average_kd": (
                self.average_kd
            ),

            "protected_seed_count": (
                self.protected_seed_count
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalSearchState:
    """
    Nodo inmutable del árbol de búsqueda GLOBAL.

    Contiene:

        teams:
            Estados parciales de los equipos.

        next_player_index:
            Índice del siguiente jugador que debe asignarse.

        assigned_count:
            Número total de jugadores ya asignados.

    Los jugadores NO se almacenan repetidamente dentro de cada nodo.

    GlobalOptimizer mantendrá una única colección:

        tuple[GlobalPlayerMetrics, ...]

    y cada equipo almacenará únicamente índices.

    ============================================================
    Ejemplo
    ============================================================

    Con 4 equipos:

        root:

            T1 []
            T2 []
            T3 []
            T4 []

        después de asignar player 0 a T1:

            T1 [0]
            T2 []
            T3 []
            T4 []

    ============================================================
    Inmutabilidad
    ============================================================

    Cada expansión genera un nuevo GlobalSearchState.

    Esto hace el backtracking mucho más seguro que modificar Team
    y posteriormente intentar deshacer cambios.
    """

    teams: tuple[
        GlobalTeamState,
        ...
    ]

    next_player_index: int = 0

    assigned_count: int = 0

    def __post_init__(
        self,
    ) -> None:
        if self.teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        normalized_teams = tuple(
            self.teams
        )

        if not normalized_teams:
            raise ValueError(
                "At least one team state is required."
            )

        if any(
            not isinstance(
                team,
                GlobalTeamState,
            )
            for team in normalized_teams
        ):
            raise TypeError(
                "teams must contain GlobalTeamState instances."
            )

        object.__setattr__(
            self,
            "teams",
            normalized_teams,
        )

        if (
            isinstance(
                self.next_player_index,
                bool,
            )
            or not isinstance(
                self.next_player_index,
                int,
            )
        ):
            raise TypeError(
                "next_player_index must be an integer."
            )

        if self.next_player_index < 0:
            raise ValueError(
                "next_player_index cannot be negative."
            )

        if (
            isinstance(
                self.assigned_count,
                bool,
            )
            or not isinstance(
                self.assigned_count,
                int,
            )
        ):
            raise TypeError(
                "assigned_count must be an integer."
            )

        if self.assigned_count < 0:
            raise ValueError(
                "assigned_count cannot be negative."
            )

        actual_assigned_count = sum(
            team.player_count
            for team in normalized_teams
        )

        if (
            actual_assigned_count
            != self.assigned_count
        ):
            raise ValueError(
                "assigned_count does not match "
                "the sum of team player counts."
            )

    # ========================================================
    # Constructores
    # ========================================================

    @classmethod
    def empty(
        cls,
        number_of_teams: int,
    ) -> GlobalSearchState:
        if (
            isinstance(
                number_of_teams,
                bool,
            )
            or not isinstance(
                number_of_teams,
                int,
            )
        ):
            raise TypeError(
                "number_of_teams must be an integer."
            )

        if number_of_teams <= 0:
            raise ValueError(
                "number_of_teams must be greater than zero."
            )

        return cls(
            teams=tuple(
                GlobalTeamState()
                for _ in range(
                    number_of_teams
                )
            ),

            next_player_index=0,

            assigned_count=0,
        )

    # ========================================================
    # Estado
    # ========================================================

    @property
    def team_count(
        self,
    ) -> int:
        return len(
            self.teams
        )

    @property
    def depth(
        self,
    ) -> int:
        return (
            self.assigned_count
        )

    def is_complete(
        self,
        player_count: int,
    ) -> bool:
        return (
            self.assigned_count
            >= player_count
        )

    def remaining_players(
        self,
        player_count: int,
    ) -> int:
        remaining = (
            player_count
            - self.assigned_count
        )

        return max(
            0,
            remaining,
        )

    def has_capacity(
        self,
        team_index: int,
        team_size: int,
    ) -> bool:
        team = self._get_team(
            team_index
        )

        return (
            team.player_count
            < team_size
        )

    def total_remaining_capacity(
        self,
        team_size: int,
    ) -> int:
        return sum(
            max(
                0,
                team_size
                - team.player_count,
            )
            for team in self.teams
        )

    # ========================================================
    # Expansión
    # ========================================================

    def assign_next_player(
        self,
        team_index: int,
        metrics: GlobalPlayerMetrics,
        team_size: int,
        protected_seed_level: int | None = 1,
        maximum_protected_seeds_per_team: int = 1,
    ) -> GlobalSearchState:
        """
        Asigna el siguiente jugador del orden global al equipo indicado.

        Este método aplica únicamente restricciones estructurales
        baratas:

            - capacidad;
            - máximo de seeds protegidos.

        Las cotas de Power/ELO/KD se implementarán posteriormente
        en GlobalBoundCalculator.
        """
        team = self._get_team(
            team_index
        )

        if (
            team.player_count
            >= team_size
        ):
            raise ValueError(
                f"Team {team_index} is already full."
            )

        is_protected_seed = (
            protected_seed_level is not None
            and metrics.seed
            == protected_seed_level
        )

        if (
            is_protected_seed
            and team.protected_seed_count
            >= maximum_protected_seeds_per_team
        ):
            raise ValueError(
                f"Team {team_index} already contains "
                "the maximum number of protected seeds."
            )

        updated_team = (
            team.add_player(
                player_index=(
                    self.next_player_index
                ),
                metrics=metrics,
                protected_seed_level=(
                    protected_seed_level
                ),
            )
        )

        updated_teams = list(
            self.teams
        )

        updated_teams[
            team_index
        ] = updated_team

        return GlobalSearchState(
            teams=tuple(
                updated_teams
            ),

            next_player_index=(
                self.next_player_index
                + 1
            ),

            assigned_count=(
                self.assigned_count
                + 1
            ),
        )

    # ========================================================
    # Symmetry breaking
    # ========================================================

    def canonical_available_team_indices(
        self,
        team_size: int,
    ) -> tuple[int, ...]:
        """
        Devuelve los equipos candidatos eliminando simetrías triviales.

        Regla:

            entre equipos vacíos equivalentes solo se permite utilizar
            el primero.

        Ejemplo:

            T1 [A]
            T2 []
            T3 []
            T4 []

        No tiene sentido explorar simultáneamente:

            B → T2
            B → T3
            B → T4

        porque esas tres ramas son equivalentes por permutación.

        Se devuelve únicamente T2 como primer equipo vacío disponible.

        Los equipos NO vacíos siguen siendo candidatos independientes.
        """
        result: list[int] = []

        first_empty_added = False

        for team_index, team in enumerate(
            self.teams
        ):
            if (
                team.player_count
                >= team_size
            ):
                continue

            if team.is_empty:
                if first_empty_added:
                    continue

                first_empty_added = True

            result.append(
                team_index
            )

        return tuple(
            result
        )

    # ========================================================
    # Métricas parciales
    # ========================================================

    @property
    def power_sums(
        self,
    ) -> tuple[float, ...]:
        return tuple(
            team.power_sum
            for team in self.teams
        )

    @property
    def elo_sums(
        self,
    ) -> tuple[float, ...]:
        return tuple(
            team.elo_sum
            for team in self.teams
        )

    @property
    def kd_sums(
        self,
    ) -> tuple[float, ...]:
        return tuple(
            team.kd_sum
            for team in self.teams
        )

    @property
    def team_sizes(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            team.player_count
            for team in self.teams
        )

    @property
    def protected_seed_counts(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            team.protected_seed_count
            for team in self.teams
        )

    # ========================================================
    # Validaciones estructurales
    # ========================================================

    def validate_capacity_feasibility(
        self,
        total_player_count: int,
        team_size: int,
    ) -> bool:
        """
        Comprueba si todavía es matemáticamente posible ubicar todos
        los jugadores restantes.

        Es una poda muy barata.
        """
        remaining_players = (
            self.remaining_players(
                total_player_count
            )
        )

        remaining_capacity = (
            self.total_remaining_capacity(
                team_size
            )
        )

        return (
            remaining_capacity
            >= remaining_players
        )

    # ========================================================
    # Equipo
    # ========================================================

    def _get_team(
        self,
        team_index: int,
    ) -> GlobalTeamState:
        if (
            isinstance(
                team_index,
                bool,
            )
            or not isinstance(
                team_index,
                int,
            )
        ):
            raise TypeError(
                "team_index must be an integer."
            )

        if not (
            0
            <= team_index
            < len(
                self.teams
            )
        ):
            raise IndexError(
                f"Invalid team_index {team_index}."
            )

        return self.teams[
            team_index
        ]

    # ========================================================
    # Serialización
    # ========================================================

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "depth": (
                self.depth
            ),

            "next_player_index": (
                self.next_player_index
            ),

            "assigned_count": (
                self.assigned_count
            ),

            "team_count": (
                self.team_count
            ),

            "team_sizes": list(
                self.team_sizes
            ),

            "power_sums": list(
                self.power_sums
            ),

            "elo_sums": list(
                self.elo_sums
            ),

            "kd_sums": list(
                self.kd_sums
            ),

            "protected_seed_counts": list(
                self.protected_seed_counts
            ),

            "teams": [
                team.as_dict()
                for team in self.teams
            ],
        }

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"depth={self.depth}, "
            f"next_player_index="
            f"{self.next_player_index}, "
            f"team_sizes={self.team_sizes})"
        )
