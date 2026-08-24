from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from numbers import Real
from typing import Any

from optimizer.global_search.global_search_problem import (
    GlobalSearchProblem,
)
from optimizer.global_search.global_search_state import (
    GlobalSearchState,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PowerTeamInterval:
    """
    Intervalo seguro de Power FINAL alcanzable por un equipo parcial.

    minimum_total:
        Menor Power total que el equipo podría acabar teniendo.

    maximum_total:
        Mayor Power total que el equipo podría acabar teniendo.

    minimum_average / maximum_average:
        El mismo intervalo expresado como Power medio final.

    IMPORTANTE:

    Estos intervalos son deliberadamente conservadores.

    Para calcular el mínimo suponemos que el equipo podría recibir
    los jugadores pendientes de menor Power.

    Para calcular el máximo suponemos que podría recibir los de
    mayor Power.

    Ignoramos que esos mismos jugadores también deben repartirse
    entre otros equipos.

    Por tanto el intervalo puede ser MÁS AMPLIO que la realidad,
    pero nunca más estrecho.

    Eso lo hace seguro para branch & bound.
    """

    team_index: int

    current_player_count: int

    remaining_slots: int

    current_power_sum: float

    minimum_total: float

    maximum_total: float

    minimum_average: float

    maximum_average: float

    def contains(
        self,
        value: float,
    ) -> bool:
        return (
            self.minimum_average
            <= value
            <= self.maximum_average
        )

    @property
    def width(
        self,
    ) -> float:
        return max(
            0.0,
            (
                self.maximum_average
                - self.minimum_average
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "team_index": (
                self.team_index
            ),

            "current_player_count": (
                self.current_player_count
            ),

            "remaining_slots": (
                self.remaining_slots
            ),

            "current_power_sum": (
                self.current_power_sum
            ),

            "minimum_total": (
                self.minimum_total
            ),

            "maximum_total": (
                self.maximum_total
            ),

            "minimum_average": (
                self.minimum_average
            ),

            "maximum_average": (
                self.maximum_average
            ),

            "width": (
                self.width
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalBoundResult:
    """
    Resultado de evaluar las cotas de un nodo GLOBAL.
    """

    feasible: bool

    upper_bound: float

    prune: bool

    reason: str | None

    incumbent_score: float

    depth: int

    capacity_feasible: bool

    seed_feasible: bool

    power_upper_bound: float

    elo_upper_bound: float

    kd_upper_bound: float

    # ========================================================
    # Diagnóstico Power
    # ========================================================

    minimum_unavoidable_power_spread: float = 0.0

    minimum_unavoidable_power_stddev: float = 0.0

    power_intervals: tuple[
        PowerTeamInterval,
        ...,
    ] = ()

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "feasible": (
                self.feasible
            ),

            "upper_bound": (
                self.upper_bound
            ),

            "prune": (
                self.prune
            ),

            "reason": (
                self.reason
            ),

            "incumbent_score": (
                self.incumbent_score
            ),

            "depth": (
                self.depth
            ),

            "capacity_feasible": (
                self.capacity_feasible
            ),

            "seed_feasible": (
                self.seed_feasible
            ),

            "power_upper_bound": (
                self.power_upper_bound
            ),

            "elo_upper_bound": (
                self.elo_upper_bound
            ),

            "kd_upper_bound": (
                self.kd_upper_bound
            ),

            "minimum_unavoidable_power_spread": (
                self.minimum_unavoidable_power_spread
            ),

            "minimum_unavoidable_power_stddev": (
                self.minimum_unavoidable_power_stddev
            ),

            "power_intervals": [
                interval.as_dict()
                for interval
                in self.power_intervals
            ],
        }


class GlobalBoundCalculator:
    """
    Calculador de cotas para GLOBAL.

    ============================================================
    Estado actual
    ============================================================

    Ya calcula de forma segura:

        - viabilidad de capacidad;
        - viabilidad de seeds;
        - intervalos alcanzables de Power;
        - mínima dispersión inevitable de Power.

    Pero todavía NO utilizamos la dispersión de Power para podar.

    `power_upper_bound` sigue siendo 100.

    Primero queremos demostrar mediante diagnóstico que los
    intervalos son correctos antes de convertirlos en una cota
    del score de PowerBalanceRestriction.
    """

    SCORE_MAXIMUM = 100.0

    def __init__(
        self,
        power_weight: float = 55.0,
        elo_balance_weight: float = 10.0,
        elo_spread_weight: float = 5.0,
        kd_weight: float = 20.0,
        team_size_weight: float = 9.0,
        seed_weight: float = 1.0,
        score_tolerance: float = 1e-6,
    ) -> None:
        weights = {
            "power_weight": (
                power_weight
            ),

            "elo_balance_weight": (
                elo_balance_weight
            ),

            "elo_spread_weight": (
                elo_spread_weight
            ),

            "kd_weight": (
                kd_weight
            ),

            "team_size_weight": (
                team_size_weight
            ),

            "seed_weight": (
                seed_weight
            ),
        }

        for (
            name,
            value,
        ) in weights.items():
            self._validate_non_negative_number(
                value=value,
                field_name=name,
            )

        self._validate_non_negative_number(
            value=score_tolerance,
            field_name="score_tolerance",
        )

        total_weight = sum(
            float(value)
            for value
            in weights.values()
        )

        if total_weight <= 0.0:
            raise ValueError(
                "At least one bound weight "
                "must be greater than zero."
            )

        self._power_weight = float(
            power_weight
        )

        self._elo_balance_weight = float(
            elo_balance_weight
        )

        self._elo_spread_weight = float(
            elo_spread_weight
        )

        self._kd_weight = float(
            kd_weight
        )

        self._team_size_weight = float(
            team_size_weight
        )

        self._seed_weight = float(
            seed_weight
        )

        self._total_weight = float(
            total_weight
        )

        self._score_tolerance = float(
            score_tolerance
        )

    # ========================================================
    # Evaluación pública
    # ========================================================

    def evaluate(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
        incumbent_score: float,
    ) -> GlobalBoundResult:
        if not isinstance(
            problem,
            GlobalSearchProblem,
        ):
            raise TypeError(
                "problem must be a GlobalSearchProblem."
            )

        if not isinstance(
            state,
            GlobalSearchState,
        ):
            raise TypeError(
                "state must be a GlobalSearchState."
            )

        incumbent = (
            self._validate_numeric(
                value=incumbent_score,
                field_name="incumbent_score",
            )
        )

        # ====================================================
        # Capacidad
        # ====================================================

        capacity_feasible = (
            state.validate_capacity_feasibility(
                total_player_count=(
                    problem.player_count
                ),

                team_size=(
                    problem.team_size
                ),
            )
        )

        if not capacity_feasible:
            return self._impossible_result(
                incumbent_score=(
                    incumbent
                ),

                state=state,

                reason=(
                    "capacity_impossible"
                ),

                capacity_feasible=False,

                seed_feasible=True,
            )

        # ====================================================
        # Seeds
        # ====================================================

        seed_feasible = (
            self._seed_feasible(
                problem=problem,
                state=state,
            )
        )

        if not seed_feasible:
            return self._impossible_result(
                incumbent_score=(
                    incumbent
                ),

                state=state,

                reason=(
                    "seed_impossible"
                ),

                capacity_feasible=True,

                seed_feasible=False,
            )

        # ====================================================
        # Power
        # ====================================================

        power_intervals = (
            self.power_intervals(
                problem=problem,
                state=state,
            )
        )

        minimum_power_spread = (
            self.minimum_unavoidable_power_spread(
                power_intervals
            )
        )

        minimum_power_stddev = (
            self.minimum_unavoidable_power_stddev(
                intervals=power_intervals,
            )
        )

        # ----------------------------------------------------
        # TODAVÍA conservador.
        #
        # El diagnóstico anterior ya funciona, pero todavía no
        # convertimos spread/stddev → score de Power Balance.
        # ----------------------------------------------------

        power_upper_bound = (
            self._power_upper_bound(
                problem=problem,
                state=state,
            )
        )

        elo_upper_bound = (
            self._elo_upper_bound(
                problem=problem,
                state=state,
            )
        )

        kd_upper_bound = (
            self._kd_upper_bound(
                problem=problem,
                state=state,
            )
        )

        upper_bound = (
            self._combine_upper_bounds(
                power_upper_bound=(
                    power_upper_bound
                ),

                elo_upper_bound=(
                    elo_upper_bound
                ),

                kd_upper_bound=(
                    kd_upper_bound
                ),
            )
        )

        prune = (
            upper_bound
            <= (
                incumbent
                + self._score_tolerance
            )
        )

        return GlobalBoundResult(
            feasible=True,

            upper_bound=(
                upper_bound
            ),

            prune=(
                prune
            ),

            reason=(
                "upper_bound"
                if prune
                else None
            ),

            incumbent_score=(
                incumbent
            ),

            depth=(
                state.depth
            ),

            capacity_feasible=True,

            seed_feasible=True,

            power_upper_bound=(
                power_upper_bound
            ),

            elo_upper_bound=(
                elo_upper_bound
            ),

            kd_upper_bound=(
                kd_upper_bound
            ),

            minimum_unavoidable_power_spread=(
                minimum_power_spread
            ),

            minimum_unavoidable_power_stddev=(
                minimum_power_stddev
            ),

            power_intervals=(
                power_intervals
            ),
        )

    # ========================================================
    # Power intervals
    # ========================================================

    def power_intervals(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> tuple[
        PowerTeamInterval,
        ...,
    ]:
        """
        Calcula el intervalo individual de Power final alcanzable
        por cada equipo.

        Para un equipo con `k` plazas libres:

            mínimo =
                Power actual
                + suma de los k Powers pendientes más bajos

            máximo =
                Power actual
                + suma de los k Powers pendientes más altos

        La misma colección de jugadores puede aparecer como posibilidad
        en varios equipos.

        Eso hace la cota optimista, que es exactamente lo que queremos
        para branch & bound.
        """

        remaining_players = (
            problem.players[
                state.next_player_index:
            ]
        )

        remaining_powers = sorted(
            float(
                player.power
            )
            for player
            in remaining_players
        )

        intervals: list[
            PowerTeamInterval
        ] = []

        for (
            team_index,
            team,
        ) in enumerate(
            state.teams
        ):
            remaining_slots = (
                problem.team_size
                - team.player_count
            )

            if remaining_slots < 0:
                raise RuntimeError(
                    f"Team {team_index} exceeds "
                    "the configured team size."
                )

            if (
                remaining_slots
                > len(
                    remaining_powers
                )
            ):
                raise RuntimeError(
                    f"Team {team_index} requires "
                    f"{remaining_slots} players but only "
                    f"{len(remaining_powers)} remain."
                )

            if remaining_slots == 0:
                minimum_addition = 0.0
                maximum_addition = 0.0

            else:
                minimum_addition = sum(
                    remaining_powers[
                        :remaining_slots
                    ]
                )

                maximum_addition = sum(
                    remaining_powers[
                        -remaining_slots:
                    ]
                )

            minimum_total = (
                team.power_sum
                + minimum_addition
            )

            maximum_total = (
                team.power_sum
                + maximum_addition
            )

            minimum_average = (
                minimum_total
                / problem.team_size
            )

            maximum_average = (
                maximum_total
                / problem.team_size
            )

            intervals.append(
                PowerTeamInterval(
                    team_index=(
                        team_index
                    ),

                    current_player_count=(
                        team.player_count
                    ),

                    remaining_slots=(
                        remaining_slots
                    ),

                    current_power_sum=(
                        float(
                            team.power_sum
                        )
                    ),

                    minimum_total=(
                        minimum_total
                    ),

                    maximum_total=(
                        maximum_total
                    ),

                    minimum_average=(
                        minimum_average
                    ),

                    maximum_average=(
                        maximum_average
                    ),
                )
            )

        return tuple(
            intervals
        )

    # ========================================================
    # Mínima dispersión inevitable
    # ========================================================

    @staticmethod
    def minimum_unavoidable_power_spread(
        intervals: tuple[
            PowerTeamInterval,
            ...,
        ],
    ) -> float:
        """
        Obtiene una cota inferior segura del spread final.

        Si todos los intervalos comparten algún valor:

            spread mínimo = 0

        Ejemplo:

            T1 [40, 55]
            T2 [44, 60]
            T3 [43, 58]
            T4 [45, 57]

        Todos podrían teóricamente acabar en 50.

        Pero:

            T1 [50, 55]
            T2 [40, 45]

        implica como mínimo:

            50 - 45 = 5

        de diferencia entre algún par de equipos.
        """

        if not intervals:
            return 0.0

        highest_lower_bound = max(
            interval.minimum_average
            for interval
            in intervals
        )

        lowest_upper_bound = min(
            interval.maximum_average
            for interval
            in intervals
        )

        return max(
            0.0,
            (
                highest_lower_bound
                - lowest_upper_bound
            ),
        )

    @staticmethod
    def minimum_unavoidable_power_stddev(
        intervals: tuple[
            PowerTeamInterval,
            ...,
        ],
    ) -> float:
        """
        Cota inferior conservadora para la desviación estándar final.

        Si existe un spread inevitable R entre el mínimo y máximo
        de n equipos, la menor desviación poblacional compatible
        únicamente con ese spread se obtiene colocando:

            un equipo en cada extremo

        y el resto en el punto medio.

        Entonces:

            stddev >= R / sqrt(2*n)

        Esta cota ignora restricciones adicionales de los intervalos,
        por lo que puede ser más baja que la real, pero no más alta.
        """

        team_count = len(
            intervals
        )

        if team_count <= 1:
            return 0.0

        spread = (
            GlobalBoundCalculator
            .minimum_unavoidable_power_spread(
                intervals
            )
        )

        if spread <= 0.0:
            return 0.0

        return (
            spread
            / sqrt(
                2.0
                * team_count
            )
        )

    # ========================================================
    # Seeds
    # ========================================================

    def _seed_feasible(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> bool:
        protected_level = (
            problem.protected_seed_level
        )

        if protected_level is None:
            return True

        maximum_per_team = (
            problem
            .maximum_protected_seeds_per_team
        )

        remaining_protected = sum(
            1
            for player_index
            in range(
                state.next_player_index,
                problem.player_count,
            )
            if (
                problem.players[
                    player_index
                ].seed
                == protected_level
            )
        )

        available_seed_slots = 0

        for team in state.teams:
            seed_slots = (
                maximum_per_team
                - team.protected_seed_count
            )

            player_slots = (
                problem.team_size
                - team.player_count
            )

            if (
                seed_slots <= 0
                or player_slots <= 0
            ):
                continue

            available_seed_slots += min(
                seed_slots,
                player_slots,
            )

        return (
            available_seed_slots
            >= remaining_protected
        )

    # ========================================================
    # Bounds blandos
    # ========================================================

    def _power_upper_bound(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> float:
        """
        Calcula una cota superior SEGURA del score de Power Balance.

        PowerBalanceRestriction utiliza:

            score =
                100 * (
                    1
                    - spread / global_average
                )

        donde:

            spread =
                max(team_average_power)
                - min(team_average_power)

        En un estado parcial no conocemos todavía el spread final,
        pero sí podemos obtener una cota inferior segura:

            minimum_unavoidable_spread

        Cuanto menor sea el spread, mayor será el score.

        Por tanto:

            minimum_unavoidable_spread
                ->
            maximum_possible_power_score

        es una cota superior válida.

        Además, como todos los equipos finales tienen el mismo tamaño,
        la media global de Power es constante para cualquier distribución
        válida de los mismos jugadores.
        """

        intervals = (
            self.power_intervals(
                problem=problem,
                state=state,
            )
        )

        minimum_spread = (
            self.minimum_unavoidable_power_spread(
                intervals
            )
        )

        # ========================================================
        # Media global exacta de Power
        # ========================================================

        total_power = sum(
            float(
                player.power
            )
            for player
            in problem.players
        )

        player_count = (
            problem.player_count
        )

        if player_count <= 0:
            return (
                self.SCORE_MAXIMUM
            )

        global_average = (
            total_power
            / player_count
        )

        # ========================================================
        # Mismo comportamiento que PowerBalanceRestriction
        # ========================================================

        if global_average <= 0.0:
            return (
                self.SCORE_MAXIMUM
                if minimum_spread <= 0.0
                else 0.0
            )

        relative_spread = (
            minimum_spread
            / global_average
        )

        score_upper_bound = (
            self.SCORE_MAXIMUM
            * (
                1.0
                - relative_spread
            )
        )

        return max(
            0.0,
            min(
                self.SCORE_MAXIMUM,
                float(
                    score_upper_bound
                ),
            ),
        )

    def _elo_upper_bound(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> float:
        return (
            self.SCORE_MAXIMUM
        )

    def _kd_upper_bound(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> float:
        return (
            self.SCORE_MAXIMUM
        )

    # ========================================================
    # Combinación
    # ========================================================

    def _combine_upper_bounds(
        self,
        power_upper_bound: float,
        elo_upper_bound: float,
        kd_upper_bound: float,
    ) -> float:
        weighted = (
            power_upper_bound
            * self._power_weight

            + elo_upper_bound
            * self._elo_balance_weight

            + elo_upper_bound
            * self._elo_spread_weight

            + kd_upper_bound
            * self._kd_weight

            + self.SCORE_MAXIMUM
            * self._team_size_weight

            + self.SCORE_MAXIMUM
            * self._seed_weight
        )

        score = (
            weighted
            / self._total_weight
        )

        return max(
            0.0,
            min(
                self.SCORE_MAXIMUM,
                float(
                    score
                ),
            ),
        )

    # ========================================================
    # Diagnóstico
    # ========================================================

    def describe_power_state(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> dict[str, Any]:
        """
        Devuelve información de Power del nodo para imprimirla
        durante pruebas.
        """

        intervals = (
            self.power_intervals(
                problem=problem,
                state=state,
            )
        )

        spread = (
            self.minimum_unavoidable_power_spread(
                intervals
            )
        )

        stddev = (
            self.minimum_unavoidable_power_stddev(
                intervals
            )
        )

        return {
            "depth": (
                state.depth
            ),

            "remaining_players": (
                problem.player_count
                - state.assigned_count
            ),

            "minimum_unavoidable_spread": (
                spread
            ),

            "minimum_unavoidable_stddev": (
                stddev
            ),

            "intervals": [
                interval.as_dict()
                for interval
                in intervals
            ],
        }

    def remaining_metric_ranges(
        self,
        problem: GlobalSearchProblem,
        state: GlobalSearchState,
    ) -> dict[
        str,
        tuple[float, float],
    ]:
        remaining = (
            problem.players[
                state.next_player_index:
            ]
        )

        if not remaining:
            return {
                "power": (
                    0.0,
                    0.0,
                ),

                "elo": (
                    0.0,
                    0.0,
                ),

                "kd": (
                    0.0,
                    0.0,
                ),
            }

        return {
            "power": (
                min(
                    player.power
                    for player
                    in remaining
                ),

                max(
                    player.power
                    for player
                    in remaining
                ),
            ),

            "elo": (
                min(
                    player.elo
                    for player
                    in remaining
                ),

                max(
                    player.elo
                    for player
                    in remaining
                ),
            ),

            "kd": (
                min(
                    player.kd
                    for player
                    in remaining
                ),

                max(
                    player.kd
                    for player
                    in remaining
                ),
            ),
        }

    # ========================================================
    # Resultado imposible
    # ========================================================

    def _impossible_result(
        self,
        incumbent_score: float,
        state: GlobalSearchState,
        reason: str,
        capacity_feasible: bool,
        seed_feasible: bool,
    ) -> GlobalBoundResult:
        return GlobalBoundResult(
            feasible=False,

            upper_bound=0.0,

            prune=True,

            reason=(
                reason
            ),

            incumbent_score=(
                incumbent_score
            ),

            depth=(
                state.depth
            ),

            capacity_feasible=(
                capacity_feasible
            ),

            seed_feasible=(
                seed_feasible
            ),

            power_upper_bound=0.0,

            elo_upper_bound=0.0,

            kd_upper_bound=0.0,

            minimum_unavoidable_power_spread=0.0,

            minimum_unavoidable_power_stddev=0.0,

            power_intervals=(),
        )

    # ========================================================
    # Validación
    # ========================================================

    @staticmethod
    def _validate_numeric(
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

        return float(
            value
        )

    @classmethod
    def _validate_non_negative_number(
        cls,
        value: Any,
        field_name: str,
    ) -> None:
        numeric = (
            cls._validate_numeric(
                value=value,
                field_name=field_name,
            )
        )

        if numeric < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"power_weight="
            f"{self._power_weight:.2f}, "
            f"elo_weight="
            f"{self._elo_balance_weight + self._elo_spread_weight:.2f}, "
            f"kd_weight="
            f"{self._kd_weight:.2f}, "
            f"score_tolerance="
            f"{self._score_tolerance:g})"
        )
