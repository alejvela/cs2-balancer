from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real
from typing import Any

from optimizer.global_search.global_search_state import (
    GlobalPlayerMetrics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalPlayerOrdering:
    """
    Ordena jugadores para la búsqueda GLOBAL.

    La idea no es ordenar simplemente del mejor al peor.

    En branch & bound queremos procesar primero los jugadores que:

        - tienen restricciones estructurales fuertes;
        - tienen valores extremos;
        - pueden provocar rápidamente desequilibrios;
        - reducen antes el espacio de búsqueda.

    ============================================================
    Prioridad
    ============================================================

    1. Seeds protegidos.

    2. Jugadores con Power extremo.

    3. Jugadores con ELO extremo.

    4. Jugadores con KD extremo.

    5. Resto de jugadores.

    ============================================================
    Determinismo
    ============================================================

    En igualdad de prioridad se utilizan:

        - Power;
        - ELO;
        - KD;
        - nickname normalizado;
        - identidad estable.

    Por tanto, la misma entrada produce siempre el mismo orden.
    """

    protected_seed_level: int | None = 1

    power_weight: float = 1.0

    elo_weight: float = 0.60

    kd_weight: float = 0.40

    seed_bonus: float = 10_000.0

    def __post_init__(
        self,
    ) -> None:
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
                    "protected_seed_level must be an integer or None."
                )

        self._validate_non_negative_number(
            self.power_weight,
            "power_weight",
        )

        self._validate_non_negative_number(
            self.elo_weight,
            "elo_weight",
        )

        self._validate_non_negative_number(
            self.kd_weight,
            "kd_weight",
        )

        self._validate_non_negative_number(
            self.seed_bonus,
            "seed_bonus",
        )

    # ========================================================
    # API pública
    # ========================================================

    def order(
        self,
        players: Sequence[
            GlobalPlayerMetrics
        ],
    ) -> tuple[
        GlobalPlayerMetrics,
        ...,
    ]:
        """
        Devuelve los jugadores en orden determinista de búsqueda.
        """
        player_list = self._validate_players(
            players
        )

        if len(player_list) <= 1:
            return tuple(
                player_list
            )

        statistics = (
            self._build_population_statistics(
                player_list
            )
        )

        decorated = [
            (
                self._priority_key(
                    player=player,
                    statistics=statistics,
                ),
                player,
            )
            for player in player_list
        ]

        decorated.sort(
            key=lambda item: item[0]
        )

        return tuple(
            player
            for _, player
            in decorated
        )

    def order_with_original_indices(
        self,
        players: Sequence[
            GlobalPlayerMetrics
        ],
    ) -> tuple[
        tuple[
            int,
            GlobalPlayerMetrics,
        ],
        ...,
    ]:
        """
        Igual que order(), pero conserva el índice original.

        Es útil cuando el solver necesita posteriormente reconstruir
        la solución con la colección original.
        """
        player_list = self._validate_players(
            players
        )

        statistics = (
            self._build_population_statistics(
                player_list
            )
        )

        decorated = [
            (
                self._priority_key(
                    player=player,
                    statistics=statistics,
                ),
                original_index,
                player,
            )
            for original_index, player
            in enumerate(
                player_list
            )
        ]

        decorated.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        return tuple(
            (
                original_index,
                player,
            )
            for (
                _,
                original_index,
                player,
            )
            in decorated
        )

    # ========================================================
    # Prioridad
    # ========================================================

    def _priority_key(
        self,
        player: GlobalPlayerMetrics,
        statistics: dict[
            str,
            float,
        ],
    ) -> tuple:
        """
        Menor tuple = mayor prioridad.
        """

        is_protected_seed = (
            self.protected_seed_level
            is not None
            and player.seed
            == self.protected_seed_level
        )

        seed_rank = (
            0
            if is_protected_seed
            else 1
        )

        power_extremeness = (
            self._normalized_distance(
                value=player.power,
                center=statistics[
                    "power_mean"
                ],
                spread=statistics[
                    "power_range"
                ],
            )
        )

        elo_extremeness = (
            self._normalized_distance(
                value=player.elo,
                center=statistics[
                    "elo_mean"
                ],
                spread=statistics[
                    "elo_range"
                ],
            )
        )

        kd_extremeness = (
            self._normalized_distance(
                value=player.kd,
                center=statistics[
                    "kd_mean"
                ],
                spread=statistics[
                    "kd_range"
                ],
            )
        )

        influence_score = (
            power_extremeness
            * self.power_weight
            +
            elo_extremeness
            * self.elo_weight
            +
            kd_extremeness
            * self.kd_weight
        )

        if is_protected_seed:
            influence_score += (
                self.seed_bonus
            )

        # sort() es ascendente.
        # Para colocar primero mayor influence_score usamos negativo.
        return (
            seed_rank,

            -influence_score,

            -player.power,

            -player.elo,

            -player.kd,

            player.nickname
            .strip()
            .casefold(),

            player.identity,
        )

    # ========================================================
    # Estadísticas de población
    # ========================================================

    @staticmethod
    def _build_population_statistics(
        players: Sequence[
            GlobalPlayerMetrics
        ],
    ) -> dict[str, float]:
        powers = [
            player.power
            for player in players
        ]

        elos = [
            player.elo
            for player in players
        ]

        kds = [
            player.kd
            for player in players
        ]

        return {
            "power_mean": (
                sum(powers)
                / len(powers)
            ),

            "power_range": (
                max(powers)
                - min(powers)
            ),

            "elo_mean": (
                sum(elos)
                / len(elos)
            ),

            "elo_range": (
                max(elos)
                - min(elos)
            ),

            "kd_mean": (
                sum(kds)
                / len(kds)
            ),

            "kd_range": (
                max(kds)
                - min(kds)
            ),
        }

    @staticmethod
    def _normalized_distance(
        value: float,
        center: float,
        spread: float,
    ) -> float:
        """
        Distancia normalizada al centro de la población.

        Si toda la población tiene el mismo valor:

            spread = 0

        entonces esa métrica no aporta prioridad.
        """
        if spread <= 0.0:
            return 0.0

        return (
            abs(
                value
                - center
            )
            / spread
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

    @staticmethod
    def _validate_non_negative_number(
        value: Any,
        field_name: str,
    ) -> None:
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

        if float(
            value
        ) < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

    # ========================================================
    # Diagnóstico
    # ========================================================

    def describe_order(
        self,
        players: Sequence[
            GlobalPlayerMetrics
        ],
    ) -> list[
        dict[str, Any]
    ]:
        """
        Devuelve un desglose útil para tests y consola.
        """
        ordered = self.order(
            players
        )

        statistics = (
            self._build_population_statistics(
                ordered
            )
        )

        result = []

        for position, player in enumerate(
            ordered,
            start=1,
        ):
            key = self._priority_key(
                player=player,
                statistics=statistics,
            )

            result.append(
                {
                    "position": position,

                    "nickname": (
                        player.nickname
                    ),

                    "seed": (
                        player.seed
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

                    "protected_seed": (
                        self.protected_seed_level
                        is not None
                        and player.seed
                        == self.protected_seed_level
                    ),

                    "priority_key": key,
                }
            )

        return result

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"protected_seed_level="
            f"{self.protected_seed_level!r}, "
            f"power_weight={self.power_weight:.2f}, "
            f"elo_weight={self.elo_weight:.2f}, "
            f"kd_weight={self.kd_weight:.2f})"
        )
