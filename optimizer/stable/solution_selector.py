from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any

from optimizer.modes.stable_optimization_config import (
    StableOptimizationConfig,
)
from optimizer.optimization_result import (
    OptimizationResult,
)
from optimizer.stable.solution_signature import (
    SolutionSignature,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SolutionComparison:
    """
    Resultado de comparar dos soluciones.

    winner:
        Resultado ganador.

    loser:
        Resultado descartado.

    reason:
        Motivo principal por el que se ha elegido el ganador.

    equivalent_score:
        True cuando ambas soluciones están dentro de la tolerancia
        configurada para la puntuación global.

    same_solution:
        True cuando ambas representan exactamente la misma composición
        lógica de equipos.
    """

    winner: OptimizationResult

    loser: OptimizationResult

    reason: str

    equivalent_score: bool = False

    same_solution: bool = False


class SolutionSelector:
    """
    Selector determinista de soluciones.

    Es responsable de responder a una pregunta:

        Dadas dos soluciones válidas,
        ¿cuál debe conservar el modo STABLE?

    La comparación utiliza una jerarquía lexicográfica:

        1. Menor penalización estructural.
        2. Mayor score global.
        3. Mejor Power Balance.
        4. Mejor ELO Balance.
        5. Mejor Rating Balance.
        6. Mejor KD Balance.
        7. Mejor ADR Balance.
        8. Firma canónica.

    IMPORTANTE:

    Las métricas secundarias solo se utilizan cuando el score global
    está empatado dentro de score_tolerance.

    Esto evita que una mejora microscópica en una métrica secundaria
    pueda derrotar a una solución objetivamente mejor según el modelo
    global.

    Finalmente, SolutionSignature garantiza que dos ejecuciones con
    exactamente los mismos candidatos seleccionen siempre la misma
    solución.
    """

    DEFAULT_RESTRICTION_PRIORITY = (
        "Power Balance",
        "ELO Balance",
        "Rating Balance",
        "KD Balance",
        "ADR Balance",
    )

    def __init__(
        self,
        config: StableOptimizationConfig,
        restriction_priority: tuple[str, ...] | None = None,
    ) -> None:
        if config is None:
            raise ValueError(
                "config cannot be None."
            )

        if not isinstance(
            config,
            StableOptimizationConfig,
        ):
            raise TypeError(
                "config must be a StableOptimizationConfig instance."
            )

        self._config = config

        if restriction_priority is None:
            restriction_priority = (
                self.DEFAULT_RESTRICTION_PRIORITY
            )

        self._restriction_priority = (
            self._validate_restriction_priority(
                restriction_priority
            )
        )

    # ========================================================
    # Selección
    # ========================================================

    def select(
        self,
        current: OptimizationResult | None,
        candidate: OptimizationResult,
    ) -> OptimizationResult:
        """
        Devuelve la mejor de las dos soluciones.

        current puede ser None durante la primera iteración.
        """
        candidate = self._validate_result(
            candidate,
            field_name="candidate",
        )

        if current is None:
            return candidate

        current = self._validate_result(
            current,
            field_name="current",
        )

        comparison = self.compare(
            current=current,
            candidate=candidate,
        )

        return comparison.winner

    def compare(
        self,
        current: OptimizationResult,
        candidate: OptimizationResult,
    ) -> SolutionComparison:
        """
        Compara dos soluciones siguiendo una jerarquía completamente
        determinista.
        """
        current = self._validate_result(
            current,
            field_name="current",
        )

        candidate = self._validate_result(
            candidate,
            field_name="candidate",
        )

        current_signature = (
            SolutionSignature.from_teams(
                current.teams
            )
        )

        candidate_signature = (
            SolutionSignature.from_teams(
                candidate.teams
            )
        )

        self._validate_same_player_pool(
            current_signature,
            candidate_signature,
        )

        same_solution = (
            current_signature
            == candidate_signature
        )

        # ----------------------------------------------------
        # 1. Penalización estructural
        # ----------------------------------------------------

        penalty_comparison = (
            self._compare_lower_is_better(
                candidate.penalty,
                current.penalty,
            )
        )

        if penalty_comparison > 0:
            return self._comparison(
                winner=candidate,
                loser=current,
                reason="lower_structural_penalty",
                same_solution=same_solution,
            )

        if penalty_comparison < 0:
            return self._comparison(
                winner=current,
                loser=candidate,
                reason="lower_structural_penalty",
                same_solution=same_solution,
            )

        # ----------------------------------------------------
        # 2. Score global
        # ----------------------------------------------------

        candidate_score = float(
            candidate.score
        )

        current_score = float(
            current.score
        )

        equivalent_score = (
            self._config.scores_equal(
                candidate_score,
                current_score,
            )
        )

        if not equivalent_score:
            if self._config.score_improves(
                candidate_score,
                current_score,
            ):
                return self._comparison(
                    winner=candidate,
                    loser=current,
                    reason="higher_score",
                    equivalent_score=False,
                    same_solution=same_solution,
                )

            return self._comparison(
                winner=current,
                loser=candidate,
                reason="higher_score",
                equivalent_score=False,
                same_solution=same_solution,
            )

        # ----------------------------------------------------
        # Si es exactamente la misma composición, no necesitamos
        # seguir buscando desempates.
        # ----------------------------------------------------

        if same_solution:
            return self._comparison(
                winner=current,
                loser=candidate,
                reason="same_solution",
                equivalent_score=True,
                same_solution=True,
            )

        # ----------------------------------------------------
        # 3-7. Restricciones secundarias
        # ----------------------------------------------------

        for restriction_name in (
            self._restriction_priority
        ):
            current_value = (
                self._restriction_score(
                    current,
                    restriction_name,
                )
            )

            candidate_value = (
                self._restriction_score(
                    candidate,
                    restriction_name,
                )
            )

            # Si ninguno de los resultados contiene esta restricción,
            # simplemente continuamos.
            if (
                current_value is None
                and candidate_value is None
            ):
                continue

            # Una restricción presente gana frente a una ausente.
            # En una ejecución normal ambas deberían tener exactamente
            # las mismas restricciones.
            if current_value is None:
                return self._comparison(
                    winner=candidate,
                    loser=current,
                    reason=(
                        "restriction_present:"
                        f"{restriction_name}"
                    ),
                    equivalent_score=True,
                    same_solution=False,
                )

            if candidate_value is None:
                return self._comparison(
                    winner=current,
                    loser=candidate,
                    reason=(
                        "restriction_present:"
                        f"{restriction_name}"
                    ),
                    equivalent_score=True,
                    same_solution=False,
                )

            restriction_comparison = (
                self._compare_higher_is_better(
                    candidate_value,
                    current_value,
                )
            )

            if restriction_comparison > 0:
                return self._comparison(
                    winner=candidate,
                    loser=current,
                    reason=(
                        "better_restriction:"
                        f"{restriction_name}"
                    ),
                    equivalent_score=True,
                    same_solution=False,
                )

            if restriction_comparison < 0:
                return self._comparison(
                    winner=current,
                    loser=candidate,
                    reason=(
                        "better_restriction:"
                        f"{restriction_name}"
                    ),
                    equivalent_score=True,
                    same_solution=False,
                )

        # ----------------------------------------------------
        # 8. Firma canónica
        # ----------------------------------------------------
        #
        # Si todo lo anterior está empatado, elegimos siempre la
        # firma lexicográficamente menor.
        #
        # Esto NO significa que sea estadísticamente mejor.
        # Es únicamente una regla estable de desempate.
        # ----------------------------------------------------

        if (
            candidate_signature
            < current_signature
        ):
            return self._comparison(
                winner=candidate,
                loser=current,
                reason="canonical_signature",
                equivalent_score=True,
                same_solution=False,
            )

        return self._comparison(
            winner=current,
            loser=candidate,
            reason="canonical_signature",
            equivalent_score=True,
            same_solution=False,
        )

    # ========================================================
    # Restricciones
    # ========================================================

    @staticmethod
    def _restriction_score(
        result: OptimizationResult,
        restriction_name: str,
    ) -> float | None:
        """
        Obtiene el score de una restricción.

        Se apoya en OptimizationResult.get_restriction(), que a su vez
        delega en ObjectiveResult.get().

        La búsqueda es case-insensitive en ObjectiveResult.
        """
        restriction = (
            result.get_restriction(
                restriction_name
            )
        )

        if restriction is None:
            return None

        score = getattr(
            restriction,
            "score",
            None,
        )

        if score is None:
            return None

        return (
            SolutionSelector._numeric(
                score,
                field_name=(
                    f"restriction "
                    f"'{restriction_name}' score"
                ),
            )
        )

    # ========================================================
    # Comparadores
    # ========================================================

    def _compare_higher_is_better(
        self,
        first: float,
        second: float,
    ) -> int:
        """
        Returns:

             1 -> first es mejor.
             0 -> equivalentes.
            -1 -> second es mejor.
        """
        first_value = self._numeric(
            first,
            field_name="first",
        )

        second_value = self._numeric(
            second,
            field_name="second",
        )

        difference = (
            first_value
            - second_value
        )

        if (
            abs(difference)
            <= self._config.score_tolerance
        ):
            return 0

        if difference > 0.0:
            return 1

        return -1

    def _compare_lower_is_better(
        self,
        first: float,
        second: float,
    ) -> int:
        """
        Returns:

             1 -> first es mejor.
             0 -> equivalentes.
            -1 -> second es mejor.
        """
        comparison = (
            self._compare_higher_is_better(
                first,
                second,
            )
        )

        return (
            -comparison
        )

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_result(
        result: OptimizationResult,
        field_name: str,
    ) -> OptimizationResult:
        if result is None:
            raise ValueError(
                f"{field_name} cannot be None."
            )

        if not isinstance(
            result,
            OptimizationResult,
        ):
            raise TypeError(
                f"{field_name} must be an "
                "OptimizationResult instance."
            )

        return result

    @staticmethod
    def _validate_same_player_pool(
        first: SolutionSignature,
        second: SolutionSignature,
    ) -> None:
        """
        No tiene sentido comparar como alternativas dos soluciones
        construidas con jugadores diferentes.
        """
        if not first.same_player_pool(
            second
        ):
            raise ValueError(
                "Cannot compare optimization results "
                "with different player pools."
            )

    @staticmethod
    def _validate_restriction_priority(
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if value is None:
            raise ValueError(
                "restriction_priority cannot be None."
            )

        try:
            items = tuple(
                value
            )

        except TypeError as error:
            raise TypeError(
                "restriction_priority must be iterable."
            ) from error

        normalized: list[str] = []

        seen: set[str] = set()

        for item in items:
            if not isinstance(
                item,
                str,
            ):
                raise TypeError(
                    "Restriction names must be strings."
                )

            name = item.strip()

            if not name:
                raise ValueError(
                    "Restriction names cannot be empty."
                )

            key = name.casefold()

            if key in seen:
                raise ValueError(
                    f"Duplicated restriction "
                    f"{name!r}."
                )

            seen.add(
                key
            )

            normalized.append(
                name
            )

        return tuple(
            normalized
        )

    @staticmethod
    def _numeric(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
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

    # ========================================================
    # Resultado comparación
    # ========================================================

    @staticmethod
    def _comparison(
        winner: OptimizationResult,
        loser: OptimizationResult,
        reason: str,
        equivalent_score: bool = False,
        same_solution: bool = False,
    ) -> SolutionComparison:
        return SolutionComparison(
            winner=winner,
            loser=loser,
            reason=reason,
            equivalent_score=equivalent_score,
            same_solution=same_solution,
        )

    # ========================================================
    # Propiedades
    # ========================================================

    @property
    def config(
        self,
    ) -> StableOptimizationConfig:
        return self._config

    @property
    def restriction_priority(
        self,
    ) -> tuple[str, ...]:
        return (
            self._restriction_priority
        )

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"tolerance="
            f"{self._config.score_tolerance:g}, "
            f"restrictions="
            f"{len(self._restriction_priority)})"
        )
