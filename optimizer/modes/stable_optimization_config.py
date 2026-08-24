from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class StableOptimizationConfig:
    """
    Configuración del modo de optimización estable.

    Este modo busca una solución reproducible y altamente convergente
    mediante múltiples reinicios deterministas.

    Objetivos principales:

        - Mejorar la calidad respecto a una única ejecución.
        - Reducir la variabilidad entre ejecuciones.
        - Detener la búsqueda cuando exista evidencia suficiente
          de convergencia.
        - Mantener un límite claro de coste computacional.

    La configuración no garantiza optimalidad matemática global.

    Para ello sería necesario un solver exacto o una demostración
    exhaustiva del espacio de soluciones.
    """

    target_score: float = 99.0

    maximum_restarts: int = 200

    minimum_restarts: int = 30

    convergence_patience: int = 25

    score_tolerance: float = 1e-6

    base_seed: int = 2026

    target_confirmation_restarts: int = 8

    minimum_unique_solutions: int = 20

    maximum_total_evaluations: int | None = None

    maximum_elapsed_seconds: float | None = None

    stop_on_perfect_score: bool = True

    perfect_score: float = 100.0

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "target_score",
            self._validate_score(
                value=self.target_score,
                field_name="target_score",
            ),
        )

        object.__setattr__(
            self,
            "perfect_score",
            self._validate_score(
                value=self.perfect_score,
                field_name="perfect_score",
            ),
        )

        object.__setattr__(
            self,
            "maximum_restarts",
            self._validate_positive_integer(
                value=self.maximum_restarts,
                field_name="maximum_restarts",
            ),
        )

        object.__setattr__(
            self,
            "minimum_restarts",
            self._validate_positive_integer(
                value=self.minimum_restarts,
                field_name="minimum_restarts",
            ),
        )

        object.__setattr__(
            self,
            "convergence_patience",
            self._validate_positive_integer(
                value=self.convergence_patience,
                field_name="convergence_patience",
            ),
        )

        object.__setattr__(
            self,
            "target_confirmation_restarts",
            self._validate_non_negative_integer(
                value=self.target_confirmation_restarts,
                field_name="target_confirmation_restarts",
            ),
        )

        object.__setattr__(
            self,
            "minimum_unique_solutions",
            self._validate_non_negative_integer(
                value=self.minimum_unique_solutions,
                field_name="minimum_unique_solutions",
            ),
        )

        object.__setattr__(
            self,
            "base_seed",
            self._validate_integer(
                value=self.base_seed,
                field_name="base_seed",
            ),
        )

        object.__setattr__(
            self,
            "score_tolerance",
            self._validate_non_negative_number(
                value=self.score_tolerance,
                field_name="score_tolerance",
            ),
        )

        object.__setattr__(
            self,
            "maximum_total_evaluations",
            self._validate_optional_positive_integer(
                value=self.maximum_total_evaluations,
                field_name="maximum_total_evaluations",
            ),
        )

        object.__setattr__(
            self,
            "maximum_elapsed_seconds",
            self._validate_optional_positive_number(
                value=self.maximum_elapsed_seconds,
                field_name="maximum_elapsed_seconds",
            ),
        )

        object.__setattr__(
            self,
            "stop_on_perfect_score",
            self._validate_boolean(
                value=self.stop_on_perfect_score,
                field_name="stop_on_perfect_score",
            ),
        )

        self._validate_relationships()

    # ========================================================
    # Relaciones entre parámetros
    # ========================================================

    def _validate_relationships(
        self,
    ) -> None:
        if (
            self.minimum_restarts
            > self.maximum_restarts
        ):
            raise ValueError(
                "minimum_restarts cannot be greater than "
                "maximum_restarts."
            )

        if (
            self.convergence_patience
            > self.maximum_restarts
        ):
            raise ValueError(
                "convergence_patience cannot be greater than "
                "maximum_restarts."
            )

        if (
            self.target_confirmation_restarts
            > self.maximum_restarts
        ):
            raise ValueError(
                "target_confirmation_restarts cannot be greater "
                "than maximum_restarts."
            )

        if (
            self.target_score
            > self.perfect_score
        ):
            raise ValueError(
                "target_score cannot be greater than "
                "perfect_score."
            )

    # ========================================================
    # Seeds
    # ========================================================

    def seed_for_restart(
        self,
        restart_index: int,
    ) -> int:
        """
        Devuelve una semilla determinista para un reinicio.

        restart_index utiliza base cero.

        Ejemplo:

            base_seed = 2026

            restart 0 -> 2026
            restart 1 -> 2027
            restart 2 -> 2028

        Esto permite que una ejecución completa sea reproducible.
        """
        validated_index = (
            self._validate_non_negative_integer(
                value=restart_index,
                field_name="restart_index",
            )
        )

        return (
            self.base_seed
            + validated_index
        )

    # ========================================================
    # Comparación de scores
    # ========================================================

    def scores_equal(
        self,
        first: float,
        second: float,
    ) -> bool:
        """
        Considera dos puntuaciones equivalentes dentro de la
        tolerancia configurada.
        """
        first_value = (
            self._validate_number(
                value=first,
                field_name="first",
            )
        )

        second_value = (
            self._validate_number(
                value=second,
                field_name="second",
            )
        )

        return (
            abs(
                first_value
                - second_value
            )
            <= self.score_tolerance
        )

    def score_improves(
        self,
        candidate: float,
        current_best: float,
    ) -> bool:
        """
        Indica si candidate mejora realmente current_best.

        Una diferencia inferior o igual a score_tolerance se considera
        empate y debe resolverse posteriormente mediante el selector
        canónico de soluciones.
        """
        candidate_value = (
            self._validate_number(
                value=candidate,
                field_name="candidate",
            )
        )

        current_value = (
            self._validate_number(
                value=current_best,
                field_name="current_best",
            )
        )

        return (
            candidate_value
            > (
                current_value
                + self.score_tolerance
            )
        )

    # ========================================================
    # Objetivos
    # ========================================================

    def target_reached(
        self,
        score: float,
    ) -> bool:
        value = self._validate_number(
            value=score,
            field_name="score",
        )

        return (
            value
            >= (
                self.target_score
                - self.score_tolerance
            )
        )

    def perfect_reached(
        self,
        score: float,
    ) -> bool:
        value = self._validate_number(
            value=score,
            field_name="score",
        )

        return (
            value
            >= (
                self.perfect_score
                - self.score_tolerance
            )
        )

    # ========================================================
    # Condiciones de parada
    # ========================================================

    def restart_limit_reached(
        self,
        completed_restarts: int,
    ) -> bool:
        validated = (
            self._validate_non_negative_integer(
                value=completed_restarts,
                field_name="completed_restarts",
            )
        )

        return (
            validated
            >= self.maximum_restarts
        )

    def minimum_search_completed(
        self,
        completed_restarts: int,
    ) -> bool:
        validated = (
            self._validate_non_negative_integer(
                value=completed_restarts,
                field_name="completed_restarts",
            )
        )

        return (
            validated
            >= self.minimum_restarts
        )

    def convergence_reached(
        self,
        completed_restarts: int,
        restarts_without_improvement: int,
        unique_solution_count: int,
    ) -> bool:
        """
        Determina si existe suficiente evidencia de convergencia.

        Se exige:

            - haber completado minimum_restarts;
            - convergence_patience reinicios sin mejorar;
            - un mínimo de soluciones únicas, cuando está configurado.

        El tercer criterio evita concluir convergencia demasiado pronto
        si las estrategias apenas han explorado el espacio.
        """
        completed = (
            self._validate_non_negative_integer(
                value=completed_restarts,
                field_name="completed_restarts",
            )
        )

        without_improvement = (
            self._validate_non_negative_integer(
                value=restarts_without_improvement,
                field_name="restarts_without_improvement",
            )
        )

        unique_count = (
            self._validate_non_negative_integer(
                value=unique_solution_count,
                field_name="unique_solution_count",
            )
        )

        if (
            completed
            < self.minimum_restarts
        ):
            return False

        if (
            without_improvement
            < self.convergence_patience
        ):
            return False

        if (
            unique_count
            < self.minimum_unique_solutions
        ):
            return False

        return True

    def target_confirmed(
        self,
        target_was_reached: bool,
        restarts_since_target: int,
    ) -> bool:
        """
        Evita detenernos inmediatamente al alcanzar target_score.

        Una vez alcanzado, seguimos varios reinicios para comprobar que
        la solución es estable y que no aparece otra mejor.
        """
        if not isinstance(
            target_was_reached,
            bool,
        ):
            raise TypeError(
                "target_was_reached must be a boolean."
            )

        if not target_was_reached:
            return False

        completed = (
            self._validate_non_negative_integer(
                value=restarts_since_target,
                field_name="restarts_since_target",
            )
        )

        return (
            completed
            >= self.target_confirmation_restarts
        )

    def evaluation_limit_reached(
        self,
        total_evaluations: int,
    ) -> bool:
        """
        Devuelve False cuando no existe límite global configurado.
        """
        if (
            self.maximum_total_evaluations
            is None
        ):
            return False

        validated = (
            self._validate_non_negative_integer(
                value=total_evaluations,
                field_name="total_evaluations",
            )
        )

        return (
            validated
            >= self.maximum_total_evaluations
        )

    def elapsed_limit_reached(
        self,
        elapsed_seconds: float,
    ) -> bool:
        """
        Devuelve False cuando no existe límite temporal configurado.
        """
        if (
            self.maximum_elapsed_seconds
            is None
        ):
            return False

        validated = (
            self._validate_non_negative_number(
                value=elapsed_seconds,
                field_name="elapsed_seconds",
            )
        )

        return (
            validated
            >= self.maximum_elapsed_seconds
        )

    # ========================================================
    # Serialización
    # ========================================================

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "target_score": (
                self.target_score
            ),

            "perfect_score": (
                self.perfect_score
            ),

            "maximum_restarts": (
                self.maximum_restarts
            ),

            "minimum_restarts": (
                self.minimum_restarts
            ),

            "convergence_patience": (
                self.convergence_patience
            ),

            "score_tolerance": (
                self.score_tolerance
            ),

            "base_seed": (
                self.base_seed
            ),

            "target_confirmation_restarts": (
                self.target_confirmation_restarts
            ),

            "minimum_unique_solutions": (
                self.minimum_unique_solutions
            ),

            "maximum_total_evaluations": (
                self.maximum_total_evaluations
            ),

            "maximum_elapsed_seconds": (
                self.maximum_elapsed_seconds
            ),

            "stop_on_perfect_score": (
                self.stop_on_perfect_score
            ),
        }

    # ========================================================
    # Fábricas
    # ========================================================

    @classmethod
    def balanced(
        cls,
    ) -> StableOptimizationConfig:
        """
        Configuración recomendada para uso habitual.

        Busca una solución estable sin disparar demasiado el coste.
        """
        return cls(
            target_score=99.0,

            maximum_restarts=150,

            minimum_restarts=25,

            convergence_patience=20,

            target_confirmation_restarts=6,

            minimum_unique_solutions=15,

            score_tolerance=1e-6,

            base_seed=2026,
        )

    @classmethod
    def exhaustive(
        cls,
    ) -> StableOptimizationConfig:
        """
        Configuración más agresiva para la composición oficial de un
        torneo.

        No es una búsqueda matemática exhaustiva; el nombre indica que
        utiliza una exploración mucho más profunda que balanced().
        """
        return cls(
            target_score=99.75,

            maximum_restarts=500,

            minimum_restarts=80,

            convergence_patience=60,

            target_confirmation_restarts=20,

            minimum_unique_solutions=50,

            score_tolerance=1e-7,

            base_seed=2026,
        )

    @classmethod
    def development(
        cls,
    ) -> StableOptimizationConfig:
        """
        Configuración rápida para pruebas durante el desarrollo.
        """
        return cls(
            target_score=98.0,

            maximum_restarts=20,

            minimum_restarts=5,

            convergence_patience=5,

            target_confirmation_restarts=2,

            minimum_unique_solutions=3,

            score_tolerance=1e-6,

            base_seed=2026,
        )

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_boolean(
        value: Any,
        field_name: str,
    ) -> bool:
        if not isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{field_name} must be a boolean."
            )

        return value

    @staticmethod
    def _validate_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
        ):
            raise TypeError(
                f"{field_name} must be an integer."
            )

        return value

    @classmethod
    def _validate_positive_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int:
        validated = (
            cls._validate_integer(
                value=value,
                field_name=field_name,
            )
        )

        if validated <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return validated

    @classmethod
    def _validate_non_negative_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int:
        validated = (
            cls._validate_integer(
                value=value,
                field_name=field_name,
            )
        )

        if validated < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return validated

    @classmethod
    def _validate_optional_positive_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int | None:
        if value is None:
            return None

        return (
            cls._validate_positive_integer(
                value=value,
                field_name=field_name,
            )
        )

    @staticmethod
    def _validate_number(
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

    @classmethod
    def _validate_non_negative_number(
        cls,
        value: Any,
        field_name: str,
    ) -> float:
        validated = (
            cls._validate_number(
                value=value,
                field_name=field_name,
            )
        )

        if validated < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return validated

    @classmethod
    def _validate_optional_positive_number(
        cls,
        value: Any,
        field_name: str,
    ) -> float | None:
        if value is None:
            return None

        validated = (
            cls._validate_number(
                value=value,
                field_name=field_name,
            )
        )

        if validated <= 0.0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return validated

    @classmethod
    def _validate_score(
        cls,
        value: Any,
        field_name: str,
    ) -> float:
        validated = (
            cls._validate_number(
                value=value,
                field_name=field_name,
            )
        )

        if not 0.0 <= validated <= 100.0:
            raise ValueError(
                f"{field_name} must be between 0 and 100."
            )

        return validated

    # ========================================================
    # Métodos especiales
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"target_score={self.target_score:.2f}, "
            f"restarts="
            f"{self.minimum_restarts}-"
            f"{self.maximum_restarts}, "
            f"patience={self.convergence_patience}, "
            f"tolerance={self.score_tolerance:g}, "
            f"base_seed={self.base_seed})"
        )
